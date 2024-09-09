from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import httpx
import asyncio

from starlette.staticfiles import StaticFiles

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./planetmint_addresses.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class PlanetmintAddress(Base):
    __tablename__ = "planetmint_addresses"
    id = Column(Integer, primary_key=True, index=True)
    address = Column(String, unique=True, index=True)


Base.metadata.create_all(bind=engine)


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def fetch_balance(address):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"https://api.rddl.io/cosmos/bank/v1beta1/balances/{address}", timeout=10.0)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPStatusError, httpx.RequestError):
            return None

    balances = {item["denom"]: int(item["amount"]) for item in data["balances"]}
    rddl = balances.get("crddl", 0) // 100000000
    staged_rddl = balances.get("stagedcrddl", 0) // 100000000
    plmnt = balances.get("plmnt", 0)

    return {"address": address, "rddl": rddl, "staged_rddl": staged_rddl, "plmnt": plmnt}


@app.get("/", response_class=HTMLResponse)
async def read_addresses(request: Request, db: Session = Depends(get_db), error: str = None):
    addresses = db.query(PlanetmintAddress).all()
    balances = await asyncio.gather(*[fetch_balance(address.address) for address in addresses])
    balances = [b for b in balances if b is not None]
    return templates.TemplateResponse("index.html", {"request": request, "balances": balances, "error": error})


@app.post("/add_address", response_class=HTMLResponse)
async def add_address(request: Request, address: str = Form(...), db: Session = Depends(get_db)):
    balance = await fetch_balance(address)
    if balance is None:
        return RedirectResponse(url=f"/?error=Invalid+address+or+API+error", status_code=303)

    db_address = PlanetmintAddress(address=address)
    db.add(db_address)
    try:
        db.commit()
    except:
        db.rollback()
        return RedirectResponse(url=f"/?error=Address+already+exists", status_code=303)

    return RedirectResponse(url="/", status_code=303)


@app.post("/delete_address/{address_id}")
async def delete_address(address_id: int, db: Session = Depends(get_db)):
    address = db.query(PlanetmintAddress).filter(PlanetmintAddress.id == address_id).first()
    if address:
        db.delete(address)
        db.commit()
    return RedirectResponse(url="/", status_code=303)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
