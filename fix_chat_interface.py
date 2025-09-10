"""Fixed chat interface function"""

async def chat_interface_fixed(
    request,
    db,
    key_resolver
):
    """
    Simplified chat interface that returns formatted messages
    """
    # Call process_natural_language directly
    result = await process_natural_language(request, db, key_resolver)
    
    if not result["success"]:
        return {
            "message": f"I couldn't process that request. {result.get('error', 'Please try rephrasing.')}",
            "success": False
        }
    
    # Use the interpretation from the AI processing
    if result.get("interpretation"):
        message = result["interpretation"]
    else:
        # Format based on result type
        message = "Query processed successfully"
    
    return {
        "message": message,
        "success": True,
        "data": result.get("result", {})
    }