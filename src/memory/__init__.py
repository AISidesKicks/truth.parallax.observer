"""The memory layer.

The OpenViking server owns the corpus, the embeddings and the index. This
package is the client the app talks to.
"""

from .viking_client import VikingClient

__all__ = ["VikingClient"]
