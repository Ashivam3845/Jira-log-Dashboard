import uvicorn

from apps import app
from apps.core.configs import settings

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(settings.PORT))
