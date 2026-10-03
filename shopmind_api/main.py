from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from shopmind_api.core.config import settings
from shopmind_api.dependencies.database import get_db
from shopmind_api.api.routes.products import router as products_router


app = FastAPI(
    title=settings.APP_NAME,
    description="Commerce backend with AI capabilities",
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)

app.include_router(products_router)


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))

    return {
        "status": "healthy",
        "database": "connected",
    }
