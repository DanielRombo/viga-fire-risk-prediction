from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from models.utilizador import Utilizador
import os

SECRET_KEY = os.getenv("SECRET_KEY", "viga-secret-key-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verificar_senha(senha_plain: str, senha_hash: str) -> bool:
    return pwd_context.verify(senha_plain, senha_hash)


def hash_senha(senha: str) -> str:
    return pwd_context.hash(senha)


def criar_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verificar_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def autenticar_utilizador(db: Session, email: str, senha: str) -> Optional[Utilizador]:
    user = db.query(Utilizador).filter(Utilizador.email == email).first()
    if not user or not verificar_senha(senha, user.senha_hash):
        return None
    return user


def get_utilizador_por_email(db: Session, email: str) -> Optional[Utilizador]:
    return db.query(Utilizador).filter(Utilizador.email == email).first()


def criar_utilizador(db: Session, nome: str, email: str, senha: str, admin: bool = False) -> Utilizador:
    user = Utilizador(
        nome=nome,
        email=email,
        senha_hash=hash_senha(senha),
        admin=admin
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
