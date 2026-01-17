from aiogram import Router
from app.presentation.telegram.handlers import setup_router as local_setup
from app.presentation.telegram.error_handlers import router as error_router

def setup_router(controller, video_service=None):
    # Get the main router which has the core logic
    main_router = local_setup(controller, video_service)
    
    # Include error handlers.
    # Note: Error handlers have specific filters (State + ~F.type).
    # Since they are specific, they can be included.
    # Aiogram checks handlers in order.
    # In 'handlers.py', we registered F.location for 'StartShiftStates.waiting_for_geo'.
    # In 'error_handlers.py', we registered ~F.location for same state.
    # These are mutually exclusive, so order doesn't matter strictly, but good practice is specific first.
    
    main_router.include_router(error_router)
    
    return main_router
