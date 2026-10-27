import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Tắt log rác
os.environ['TF_NUM_INTEROP_THREADS'] = '1'  # Giảm luồng
os.environ['TF_NUM_INTRAOP_THREADS'] = '1'

from app import create_app
import tensorflow as tf

# Cấu hình TensorFlow chỉ dùng 1 luồng
tf.config.threading.set_inter_op_parallelism_threads(1)
tf.config.threading.set_intra_op_parallelism_threads(1)

app = create_app()

if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=debug, host=host, port=port)