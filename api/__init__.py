# API package


def register_blueprints(app):
    from api.auth_routes import bp as auth_bp
    from api.dashboard_routes import bp as dashboard_bp
    from api.fraud_routes import bp as fraud_bp
    from api.investigation_routes import bp as investigation_bp
    from api.transaction_routes import bp as transaction_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(transaction_bp)
    app.register_blueprint(fraud_bp)
    app.register_blueprint(investigation_bp)
    app.register_blueprint(dashboard_bp)
