from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from config.database import get_db
from services.auth import (
    autenticar_utilizador, criar_token, verificar_token,
    criar_utilizador, get_utilizador_por_email
)
from models.utilizador import Utilizador

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class RegistoSchema(BaseModel):
    nome: str
    email: str
    senha: str


class TokenSchema(BaseModel):
    access_token: str
    token_type: str
    utilizador: dict


def get_utilizador_atual(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Utilizador:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = verificar_token(token)
    if not payload:
        raise credentials_exception
    email = payload.get("sub")
    if not email:
        raise credentials_exception
    user = get_utilizador_por_email(db, email)
    if not user or not user.ativo:
        raise credentials_exception
    return user


@router.post("/auth/registar", response_model=TokenSchema)
def registar(dados: RegistoSchema, db: Session = Depends(get_db)):
    if get_utilizador_por_email(db, dados.email):
        raise HTTPException(status_code=400, detail="Email já registado")
    user = criar_utilizador(db, dados.nome, dados.email, dados.senha)
    token = criar_token({"sub": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "utilizador": {"id": user.id, "nome": user.nome, "email": user.email, "admin": user.admin}
    }


@router.post("/auth/login", response_model=TokenSchema)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = autenticar_utilizador(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = criar_token({"sub": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "utilizador": {"id": user.id, "nome": user.nome, "email": user.email, "admin": user.admin}
    }


@router.get("/auth/me")
def me(utilizador: Utilizador = Depends(get_utilizador_atual)):
    return {
        "id": utilizador.id,
        "nome": utilizador.nome,
        "email": utilizador.email,
        "admin": utilizador.admin,
        "criado_em": utilizador.criado_em
    }


@router.post("/auth/logout")
def logout():
    return {"mensagem": "Logout efetuado com sucesso"}
