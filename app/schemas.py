from pydantic import BaseModel, Field


class DecisionAnalysisRequest(BaseModel):
    category: str = Field(..., min_length=2, description="Categoria da decisão")
    question: str = Field(..., min_length=5, description="Pergunta principal do usuário")
    context: str = Field(..., min_length=20, description="Contexto da decisão")


class DecisionCategory(BaseModel):
    id: str
    name: str
    example: str
