import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import Flask, render_template

from app.config import config_by_name
from app.extensions import db, migrate
from app.routes import main_bp, militaries_bp, military_teams_bp, teams_bp


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    selected_config = config_name or "development"
    app.config.from_object(config_by_name[selected_config])

    _ensure_runtime_directories(app)
    _configure_logging(app)
    _initialize_extensions(app)
    _register_blueprints(app)
    _register_error_handlers(app)

    app.logger.info("Aplicacao Escala de Servico inicializada")
    return app


def _ensure_runtime_directories(app: Flask) -> None:
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["LOG_DIR"]).mkdir(parents=True, exist_ok=True)


def _initialize_extensions(app: Flask) -> None:
    db.init_app(app)
    from app import models  # noqa: F401
    migrate.init_app(app, db)


def _register_blueprints(app: Flask) -> None:
    app.register_blueprint(main_bp)
    app.register_blueprint(militaries_bp)
    app.register_blueprint(teams_bp)
    app.register_blueprint(military_teams_bp)


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def not_found(error):
        app.logger.warning("Pagina nao encontrada: %s", error)
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.exception("Erro interno da aplicacao: %s", error)
        return render_template("errors/500.html"), 500


def _configure_logging(app: Flask) -> None:
    if app.testing:
        app.logger.setLevel(logging.CRITICAL)
        return

    log_file = Path(app.config["LOG_DIR"]) / "escala.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=app.config["LOG_MAX_BYTES"],
        backupCount=app.config["LOG_BACKUP_COUNT"],
        encoding="utf-8",
    )
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s"
        )
    )
    file_handler.setLevel(app.config["LOG_LEVEL"])

    app.logger.addHandler(file_handler)
    app.logger.setLevel(app.config["LOG_LEVEL"])
