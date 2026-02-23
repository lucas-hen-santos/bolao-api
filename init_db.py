# init_db.py
from app.db.session import engine
from app.db.base import Base

# IMPORTANTE: Importar todos os modelos aqui para que o SQLAlchemy
# saiba que eles existem antes de criar as tabelas
from app.models.user import User
from app.models.season import Season, RealDriver, RealTeam
from app.models.team import Team
from app.models.race import Race, RaceResult
from app.models.bet import Bet
from app.models.achievement import Achievement, UserAchievement
from app.models.rivalry import Rivalry
from app.models.ranking_cache import RankingCache
from app.models.subscription import PushSubscription


def init_db():
    print("Conectando ao banco de dados...")
    print("Criando tabelas...")
    
    # Cria todas as tabelas definidas nos modelos importados acima
    Base.metadata.create_all(bind=engine)
    
    print("Tabelas criadas com sucesso! Verifique seu MySQL.")

if __name__ == "__main__":
    init_db()