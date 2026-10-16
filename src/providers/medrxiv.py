"""medRxiv uses the same public API as bioRxiv, with a separate server name."""

from providers import biorxiv


async def get_urls(session, identifier):
    return await biorxiv.get_urls(session, identifier, server="medrxiv")
