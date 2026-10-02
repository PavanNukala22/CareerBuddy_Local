"""
Prompt-kit item: "GD Interruption Responsiveness" (FR-GD-04). Verifies, against
the real GDConsumer over a real Channels WebSocket test harness (not a mock of
the consumer itself), that:
  1. sending {"action": "user_speaking"} while an agent turn is mid-generation
     stops that turn from ever being broadcast — the in-flight
     asyncio.to_thread(get_agent_response, ...) call is genuinely cancelled,
     not just ignored client-side;
  2. after {"action": "user_message", ...}, the agent rotation resumes and
     produces further turns.
get_agent_response is patched to a slow, then fast, blocking call so timing is
deterministic rather than depending on a real Sarvam round-trip.
"""
import time
from unittest import mock

from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User
from django.test import TransactionTestCase

from GD_app.consumers import GDConsumer
from GD_app.models import GDSession


class GDInterruptionResponsivenessTests(TransactionTestCase):
    async def _make_communicator(self, session, user):
        communicator = WebsocketCommunicator(
            GDConsumer.as_asgi(), f"/ws/GD_app/{session.id}/"
        )
        communicator.scope["url_route"] = {"kwargs": {"session_id": str(session.id)}}
        communicator.scope["user"] = user
        return communicator

    async def test_user_speaking_cancels_the_in_flight_agent_turn_and_resume_continues(self):
        user = await self._get_or_create_user("qa_gd_interrupt_user")
        session = await self._create_session(user)

        call_count = {"n": 0}

        def slow_then_fast_agent_response(agent_key, topic, history, language):
            call_count["n"] += 1
            if call_count["n"] == 1:
                # Simulates a turn genuinely "in progress" when the user interrupts.
                time.sleep(1.2)
                return "SHOULD_NEVER_BE_BROADCAST_FIRST_TURN"
            return "RESUMED_TURN_RESPONSE"

        with mock.patch("GD_app.consumers.get_agent_response", side_effect=slow_then_fast_agent_response):
            communicator = await self._make_communicator(session, user)
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            await communicator.send_json_to({"action": "start"})

            # 'status' (started) then Rishi's opening 'message' arrive immediately.
            frame1 = await communicator.receive_json_from(timeout=5)
            self.assertEqual(frame1.get("type"), "status")
            frame2 = await communicator.receive_json_from(timeout=5)
            self.assertEqual(frame2.get("type"), "message")
            self.assertEqual(frame2.get("speaker"), "rishi")

            # Alex's turn begins: a 'typing' indicator fires, then the (slow,
            # 1.2s) get_agent_response call starts in a background thread.
            frame3 = await communicator.receive_json_from(timeout=5)
            self.assertEqual(frame3.get("type"), "typing")

            # Interrupt WELL before the 1.2s call would resolve.
            await communicator.send_json_to({"action": "user_speaking"})
            status_frame = await communicator.receive_json_from(timeout=5)
            self.assertEqual(status_frame, {"type": "status", "status": "user_speaking"})

            # No agent 'message' frame should ever arrive for the cancelled turn,
            # even though the mocked call is still "in flight" for another ~1s.
            no_message_arrived = await communicator.receive_nothing(timeout=1.6)
            self.assertTrue(
                no_message_arrived,
                "the interrupted agent turn's response was broadcast anyway — cancellation is not real",
            )

            # Submit the user's own turn — this must be stored/broadcast and resume the loop.
            await communicator.send_json_to({"action": "user_message", "content": "Here is my point on the topic."})
            user_msg_frame = await communicator.receive_json_from(timeout=5)
            self.assertEqual(user_msg_frame.get("type"), "message")
            self.assertTrue(user_msg_frame.get("is_user"))
            self.assertEqual(user_msg_frame.get("content"), "Here is my point on the topic.")

            # Rotation resumes: a new 'typing' frame, then the (fast, mocked)
            # resumed turn's 'message' — proving the loop picked back up.
            resumed_typing = await communicator.receive_json_from(timeout=5)
            self.assertEqual(resumed_typing.get("type"), "typing")
            resumed_message = await communicator.receive_json_from(timeout=5)
            self.assertEqual(resumed_message.get("type"), "message")
            self.assertEqual(resumed_message.get("content"), "RESUMED_TURN_RESPONSE")

            await communicator.disconnect()

    async def _get_or_create_user(self, username):
        from channels.db import database_sync_to_async

        @database_sync_to_async
        def _go():
            user, _ = User.objects.get_or_create(username=username)
            return user

        return await _go()

    async def _create_session(self, user):
        from channels.db import database_sync_to_async

        @database_sync_to_async
        def _go():
            GDSession.objects.filter(topic="QA-INTERRUPTION-TOPIC").delete()
            return GDSession.objects.create(topic="QA-INTERRUPTION-TOPIC", user=user)

        return await _go()
