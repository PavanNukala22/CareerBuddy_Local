"""
WebSocket consumer for the Group Discussion feature.
Manages real-time AI agent turns, user interruptions, and session state.
"""
import asyncio
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

from .agents import AGENTS, AGENT_ORDER, get_agent_response, analyze_user_performance

logger = logging.getLogger(__name__)


class GDConsumer(AsyncWebsocketConsumer):
    """One WebSocket connection = one GD session."""

    async def connect(self):
        self.session_id = int(self.scope['url_route']['kwargs']['session_id'])
        self.group_name = f'gd_{self.session_id}'
        self.is_paused = False          # True when user is speaking
        self.is_running = False         # True when agent loop is active
        self.current_agent_index = 0   # cycles through AGENT_ORDER
        self._agent_task = None
        # Language chosen in the header dropdown. gd.js has always sent this on
        # 'start'/'resume'; it was simply never read, so the discussion stayed
        # in English whatever the learner picked.
        self.language = 'english'

        # Same ownership check as the HTTP room/report views: without it, any
        # authenticated (or even anonymous) socket could join another user's
        # session group and receive their live transcript in real time.
        user = self.scope.get('user')
        if not user or not user.is_authenticated or not await self._is_session_owner(user):
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info(f"[GD {self.session_id}] WebSocket connected")

    @database_sync_to_async
    def _is_session_owner(self, user):
        from .models import GDSession
        return GDSession.objects.filter(id=self.session_id, user=user).exists()

    async def disconnect(self, close_code):
        self.is_running = False
        if self._agent_task and not self._agent_task.done():
            self._agent_task.cancel()
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info(f"[GD {self.session_id}] WebSocket disconnected")

    # ── Receive messages from the browser ────────────────────────────────────
    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')

        if action == 'start':
            self.language = (data.get('language') or 'english').strip().lower()
            await self._start_discussion()

        elif action == 'user_speaking':
            # User pressed "Speak" — pause AI agents immediately
            self.is_paused = True
            self.is_running = False
            if self._agent_task and not self._agent_task.done():
                self._agent_task.cancel()
            await self._send({'type': 'status', 'status': 'user_speaking'})

        elif action == 'user_message':
            # User finished speaking; add their message then resume
            content = data.get('content', '').strip()
            if content:
                await self._save_message('user', content, is_user=True)
                await self._send({
                    'type': 'message',
                    'speaker': 'user',
                    'speaker_name': 'You',
                    'avatar': '🧑',
                    'color': '#F59E0B',
                    'content': content,
                    'is_user': True,
                })
            self.is_paused = False
            await self._resume_discussion()

        elif action == 'end':
            await self._end_session()

    # ── Discussion lifecycle ──────────────────────────────────────────────────
    async def _start_discussion(self):
        session = await self._get_session()
        topic = session.topic

        await self._send({'type': 'status', 'status': 'started', 'topic': topic})

        # Opening remark by Rishi (moderator)
        opening = f"Welcome everyone! Today we're discussing: \"{topic}\". Let's dive in — Alex, would you like to start?"
        await self._save_message('rishi', opening)
        await self._send({
            'type': 'message',
            'speaker': 'rishi',
            'speaker_name': 'Rishi',
            'avatar': AGENTS['rishi']['avatar'],
            'color': AGENTS['rishi']['color'],
            'content': opening,
            'is_user': False,
        })

        self.is_running = True
        self.current_agent_index = 0
        self._agent_task = asyncio.create_task(self._agent_loop(topic))

    async def _resume_discussion(self):
        session = await self._get_session()
        self.is_running = True
        self._agent_task = asyncio.create_task(self._agent_loop(session.topic))

    async def _agent_loop(self, topic: str):
        """Continuously cycle through agents until paused or stopped."""
        try:
            while self.is_running and not self.is_paused:
                agent_key = AGENT_ORDER[self.current_agent_index % len(AGENT_ORDER)]
                agent = AGENTS[agent_key]

                # Signal "agent is typing"
                await self._send({
                    'type': 'typing',
                    'speaker': agent_key,
                    'speaker_name': agent['name'],
                    'avatar': agent['avatar'],
                    'color': agent['color'],
                })

                # Fetch conversation history for context
                history = await self._get_history()

                # Call Groq API in thread pool (blocking I/O)
                if not self.is_running or self.is_paused:
                    break
                response = await asyncio.to_thread(
                    get_agent_response, agent_key, topic, history, self.language
                )

                if not self.is_running or self.is_paused:
                    break

                # Save & broadcast
                await self._save_message(agent_key, response)
                await self._send({
                    'type': 'message',
                    'speaker': agent_key,
                    'speaker_name': agent['name'],
                    'avatar': agent['avatar'],
                    'color': agent['color'],
                    'content': response,
                    'is_user': False,
                })

                self.current_agent_index += 1

                # Natural pause between agents (2-3 s)
                if self.is_running and not self.is_paused:
                    await asyncio.sleep(2.5)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[GD {self.session_id}] Agent loop error: {e}")

    async def _end_session(self):
        self.is_running = False
        if self._agent_task and not self._agent_task.done():
            self._agent_task.cancel()

        await self._send({'type': 'status', 'status': 'analyzing'})

        # Mark DB session as ended
        await self._mark_ended()

        # Analyze user performance
        history = await self._get_history()
        session = await self._get_session()
        report = await asyncio.to_thread(
            analyze_user_performance, session.topic, history, self.language
        )

        # Save report to DB
        await self._save_report(report)

        await self._send({'type': 'report', 'report': report})
        await self._send({'type': 'status', 'status': 'ended'})

    # ── Helpers ───────────────────────────────────────────────────────────────
    async def _send(self, data: dict):
        try:
            await self.send(text_data=json.dumps(data))
        except Exception:
            pass

    @database_sync_to_async
    def _get_session(self):
        from .models import GDSession
        return GDSession.objects.get(id=self.session_id)

    @database_sync_to_async
    def _get_history(self):
        from .models import GDMessage
        msgs = GDMessage.objects.filter(session_id=self.session_id).order_by('timestamp')
        return [
            {
                'speaker': m.speaker,
                'speaker_name': next(
                    (a['name'] for k, a in AGENTS.items() if k == m.speaker),
                    'You'
                ),
                'content': m.content,
                'is_user': m.is_user,
            }
            for m in msgs
        ]

    @database_sync_to_async
    def _save_message(self, speaker: str, content: str, is_user: bool = False):
        from .models import GDMessage, GDSession
        session = GDSession.objects.get(id=self.session_id)
        GDMessage.objects.create(
            session=session,
            speaker=speaker,
            content=content,
            is_user=is_user,
        )

    @database_sync_to_async
    def _mark_ended(self):
        from .models import GDSession
        GDSession.objects.filter(id=self.session_id).update(
            is_active=False, ended_at=timezone.now()
        )

    @database_sync_to_async
    def _save_report(self, report: dict):
        from .models import GDSession
        session = GDSession.objects.get(id=self.session_id)
        session.performance_report = report
        session.save()

        # Save to shared ScoreRecord
        if session.user and report.get('overall_score') is not None:
            try:
                from core.models import ScoreRecord
                raw_score = report['overall_score']
                scaled_score = round(raw_score / 4.0, 1)
                ScoreRecord.objects.create(
                    user=session.user,
                    module='gd',
                    score=scaled_score,
                    max_score=25,
                    label=f"GD: {session.topic}"
                )
            except Exception:
                pass  # Score recording is optional; don't fail the session
