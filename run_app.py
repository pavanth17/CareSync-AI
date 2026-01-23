from app import app, socketio

if __name__ == '__main__':
    try:
        print("Runtime URL Map:", app.url_map)
        @app.route('/ping')
        def ping(): return "pong"
        # Run the app with allow_unsafe_werkzeug to permit running with debug=False/True as needed
        socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
    except Exception as e:
        import traceback
        traceback.print_exc()
