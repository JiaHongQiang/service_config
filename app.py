from flask import Flask

def create_app():
    app = Flask(__name__)
    app.secret_key = 'your-secret-key-here'  # 在生产环境中应该使用更安全的密钥
    
    # 注册蓝图
    from routes import api_bp
    app.register_blueprint(api_bp)
    
    # 提供 favicon.ico 文件
    @app.route('/favicon.ico')
    def favicon():
        return app.send_static_file('favicon.ico')
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)