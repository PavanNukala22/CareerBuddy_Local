import json
import logging
import time
import functools
from django.http import JsonResponse

logger = logging.getLogger(__name__)


class AgentInputError(Exception):
    """A problem with the learner's submission that retrying cannot fix.

    Message is written for the learner and reaches them verbatim (no
    "Internal agent error:" prefix). safe_run does not retry it.
    """
    pass


class BaseAgent:
    def __init__(self, module_name):
        self.module_name = module_name

    def safe_run(self, payload, retries=3):
        input_size = len(str(payload))
        start_time = time.time()
        last_error = None

        for attempt in range(1, retries + 1):
            try:
                result = self.run(payload)
                duration = time.time() - start_time
                logger.info(f"Agent {self.module_name} success. Duration: {duration:.2f}s. Input: {input_size}")
                return {
                    "success": True,
                    "data": result,
                    "error": None,
                    "meta": {
                        "module": self.module_name,
                        "duration": round(duration, 3),
                        "attempt": attempt
                    }
                }
            except AgentInputError as e:
                # Learner must fix the submission; retrying wastes time and the
                # message is guidance, so return it verbatim without a prefix.
                duration = time.time() - start_time
                logger.info(f"Agent {self.module_name} input rejected: {e}")
                return {
                    "success": False,
                    "data": {},
                    "error": str(e),
                    "meta": {
                        "module": self.module_name,
                        "duration": round(duration, 3),
                        "attempt": attempt
                    }
                }
            except Exception as e:
                last_error = str(e)
                logger.error(f"Agent {self.module_name} attempt {attempt} failed: {last_error}")
                time.sleep(0.5 * attempt) # Incremental backoff

        duration = time.time() - start_time
        logger.error(f"Agent {self.module_name} exhausted all {retries} retries. Final error: {last_error}")
        return {
            "success": False,
            "data": {},
            "error": f"Internal agent error: {last_error}",
            "meta": {
                "module": self.module_name,
                "duration": round(duration, 3),
                "attempt": retries
            }
        }

    def run(self, payload):
        raise NotImplementedError("Subclasses must implement run()")

def api_view_wrapper(view_func):
    @functools.wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        try:
            response = view_func(request, *args, **kwargs)
            if isinstance(response, JsonResponse):
                # Ensure it has success/data/error structure if possible
                # But if it's already a JsonResponse, we assume it's mostly fine
                # unless it's missing the keys the user wants.
                content = json.loads(response.content)
                if not all(k in content for k in ["success", "data", "error"]):
                    # Repackage
                    success = response.status_code < 400
                    error = content.get("error") if not success else None
                    data = content if success else {}
                    if "error" in data: del data["error"]
                    
                    return JsonResponse({
                        "success": success,
                        "data": data,
                        "error": error
                    }, status=response.status_code)
                return response
            return response
        except Exception as e:
            logger.exception(f"Unhandled API Exception in {view_func.__name__}: {str(e)}")
            return JsonResponse({
                "success": False,
                "data": {},
                "error": f"A system error occurred: {str(e)}"
            }, status=500)
    return wrapped_view
