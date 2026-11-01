# api/models/escritorio_evento.py — AJUSTA
# Trilha dos atos de ciclo de vida da empresa: arquivar, restaurar, excluir (migration 054).
#
# POR QUE ESTA TABELA EXISTE SEPARADA. 'enquadramento_evento' referencia estabelecimentos com ON
# DELETE CASCADE, e os estabelecimentos somem quando a empresa e excluida. Registrar a exclusao
# la seria gravar a linha e apaga-la no mesmo ato.
#
# Por isso aqui NAO ha chave estrangeira para empresas, e a razao social e o CNPJ sao COPIADOS no
# instante do ato: e o que responde "qual empresa?" quando nao ha mais empresa.
#
# Carolina, 22/10: "a exclusao, quando permitida, fica registrada na trilha de eventos do
# escritorio: quem excluiu, quando e qual empresa (razao social e CNPJ), mesmo depois de os dados
# da empresa sumirem."
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base

# Vocabulario fechado, espelhando o CHECK da migration. Importar daqui evita a string solta no
# meio do router, que e como um "arquivada " com espaco entra no banco e nunca mais sai.
EVENTO_ARQUIVADA = "arquivada"
EVENTO_RESTAURADA = "restaurada"
EVENTO_EXCLUIDA = "excluida"
# Exclusao de ESTABELECIMENTO (migration 063). Entra na mesma trilha, e nao numa tabela propria,
# porque e o mesmo fato para quem audita: um cadastro do escritorio deixou de existir, por ato de
# alguem. 'enquadramento_evento' nao serviria — ela referencia estabelecimentos com ON DELETE
# CASCADE, e a linha sumiria junto com o que ela registra.
EVENTO_ESTAB_EXCLUIDO = "estabelecimento_excluido"
EVENTOS_ESCRITORIO = (EVENTO_ARQUIVADA, EVENTO_RESTAURADA, EVENTO_EXCLUIDA, EVENTO_ESTAB_EXCLUIDO)

ROTULO_EVENTO_ESCRITORIO = {
    EVENTO_ARQUIVADA: "Arquivada",
    EVENTO_RESTAURADA: "Restaurada",
    EVENTO_EXCLUIDA: "Excluída",
    EVENTO_ESTAB_EXCLUIDO: "Estabelecimento excluído",
}


class EscritorioEvento(Base):
    __tablename__ = "escritorio_evento"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # escritorio_id NAO e mapeado, como nas demais tabelas do projeto: quem preenche e o trigger
    # trg_fill_escritorio, a partir da GUC app.escritorio. Mapear abriria caminho para o codigo
    # informar um escritorio, e a chave de isolamento nao pode vir do cliente.

    evento: Mapped[str] = mapped_column(String(24), nullable=False)

    # Referencia FRACA, sem ForeignKey: depois da exclusao este id nao aponta para linha alguma.
    empresa_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    razao_social: Mapped[str] = mapped_column(String(300), nullable=False)
    cnpj: Mapped[str | None] = mapped_column(String(20))

    autor: Mapped[str] = mapped_column(String(200), nullable=False)
    ocorrido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    detalhe: Mapped[str | None] = mapped_column(String(500))

    # O ESTABELECIMENTO EXCLUIDO (migration 063), quando o evento for desse tipo. Nulos nos
    # eventos de empresa.
    #
    # Colunas proprias, e nao reaproveitamento de 'razao_social'/'cnpj': aquelas duas respondem
    # QUAL EMPRESA, e continuam respondendo isso tambem nestas linhas — sem elas, a trilha nao
    # diria de qual cliente se tratava. Misturar os dois faria 'cnpj' ser as vezes da empresa e as
    # vezes do estabelecimento, sem nada no dado que dissesse qual.
    estabelecimento_nome: Mapped[str | None] = mapped_column(String(300))
    estabelecimento_cnpj: Mapped[str | None] = mapped_column(String(20))
