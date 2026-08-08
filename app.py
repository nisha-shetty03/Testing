import os
import io
import json
import random
import numpy as np
from PIL import Image

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# ---------------------------------------------------------------------------
# Plant health model loading
#
# Put a trained model at models/plant_health_model.tflite (produced by
# train.py or train_full_colab.py) and models/class_names.json next to this
# file. If they're not present, the endpoint below falls back to the old
# simulated/random behavior so the app keeps running either way.
# ---------------------------------------------------------------------------
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
TFLITE_PATH = os.path.join(MODEL_DIR, 'plant_health_model.tflite')
CLASS_NAMES_PATH = os.path.join(MODEL_DIR, 'class_names.json')
IMG_SIZE = (160, 160)

plant_interpreter = None
plant_class_names = None
plant_model_load_error = None

def load_plant_model():
    global plant_interpreter, plant_class_names, plant_model_load_error
    if not (os.path.exists(TFLITE_PATH) and os.path.exists(CLASS_NAMES_PATH)):
        plant_model_load_error = f"Model files not found at {TFLITE_PATH}"
        print('[plant_health]', plant_model_load_error, '- using simulated predictions until a model is added.')
        return
    try:
        try:
            from ai_edge_litert.interpreter import Interpreter
            print('[plant_health] Using ai_edge_litert')
        except ImportError as e0:
            print('[plant_health] ai_edge_litert unavailable (', e0, '), trying tflite_runtime')
            try:
                from tflite_runtime.interpreter import Interpreter
                print('[plant_health] Using tflite_runtime')
            except ImportError as e1:
                print('[plant_health] tflite_runtime unavailable (', e1, '), trying tensorflow.lite')
                from tensorflow.lite.python.interpreter import Interpreter
        plant_interpreter = Interpreter(model_path=TFLITE_PATH)
        plant_interpreter.allocate_tensors()
        with open(CLASS_NAMES_PATH) as f:
            plant_class_names = json.load(f)
        print(f'[plant_health] Loaded model with {len(plant_class_names)} classes.')
    except Exception as e:
        plant_model_load_error = f"{type(e).__name__}: {e}"
        print('[plant_health] Failed to load model, falling back to simulated predictions:', plant_model_load_error)
        plant_interpreter = None

load_plant_model()

# Maps disease-name keywords -> one of the original recommendation "buckets"
# (kept from the app's existing translated recommendation lists, so hi/kn
# recommendations stay available without needing a full 38-class translation
# table). 0=healthy, 1=fungal/blight, 2=spot/mildew/rust, 3=nutrient,
# 4=pest/virus.
_KEYWORD_TO_BUCKET = [
    (['healthy'], 0),
    (['blight', 'rot', 'mold', 'mould'], 1),
    (['scab', 'spot', 'mildew', 'rust', 'measles'], 2),
    (['deficiency'], 3),
    (['virus', 'mite', 'pest', 'greening', 'bacterial'], 4),
]

def classify_condition(condition_lower):
    for keywords, bucket in _KEYWORD_TO_BUCKET:
        if any(k in condition_lower for k in keywords):
            return bucket
    return 1  # default to the general fungal/treatment bucket

def run_plant_inference(image_bytes):
    """Returns (crop, condition, confidence) or None if no model is loaded."""
    if plant_interpreter is None:
        return None
    img = Image.open(io.BytesIO(image_bytes)).convert('RGB').resize(IMG_SIZE)
    arr = np.asarray(img, dtype=np.float32)[np.newaxis, ...]  # (1, H, W, 3), 0-255

    input_details = plant_interpreter.get_input_details()
    output_details = plant_interpreter.get_output_details()
    plant_interpreter.set_tensor(input_details[0]['index'], arr)
    plant_interpreter.invoke()
    output = plant_interpreter.get_tensor(output_details[0]['index'])[0]

    idx = int(np.argmax(output))
    confidence = float(output[idx])
    class_name = plant_class_names[idx]

    if '___' in class_name:
        crop, condition = class_name.split('___', 1)
    else:
        crop, condition = '', class_name
    condition = condition.replace('_', ' ').strip()
    return crop.replace('_', ' ').strip(), condition, confidence

# Translation dictionaries for UI
TRANSLATIONS = {
    'en': {
        'changeLangBtn': 'Change Language',
        'currentLang': 'English',
        'appTitle': 'Agricultural Detection System',
        'chooseText': 'Choose what you want to analyze:',
        'soilDetectionTitle': 'Soil Detection',
        'soilDetectionDesc': 'Analyze land type, climate, and get crop suggestions',
        'plantHealthTitle': 'Plant Health',
        'plantHealthDesc': 'Check plant health and get treatment recommendations',
        'backBtn': 'Back',
        'soilTitle': 'Soil Detection',
        'uploadLandLabel': 'Upload Land Image:',
        'analyzeBtn': 'Analyze Soil',
        'resultsTitle': 'Analysis Results:',
        'landTypeLabel': 'Land Type:',
        'climateLabel': 'Climate:',
        'waterLabel': 'Water Facility:',
        'phLabel': 'Soil pH:',
        'yieldLabel': 'Predicted Yield:',
        'suitabilityLabel': 'Suitability:',
        'suggestedCropsLabel': 'Suggested Crops:',
        'plantTitle': 'Plant Health Check',
        'uploadPlantLabel': 'Upload Plant Image:',
        'checkHealthBtn': 'Check Plant Health',
        'healthResultsTitle': 'Health Report:',
        'healthStatusLabel': 'Health Status:',
        'healthScoreLabel': 'Health Score:',
        'detectedIssuesLabel': 'Detected Issues:',
        'recommendationsLabel': 'Recommendations:',
        'chatTitle': 'AI Assistant',
        'welcomeMessage': 'Hello! How can I help you today?',
        'sendBtn': 'Send'
    },
    'hi': {
        'changeLangBtn': 'भाषा बदलें',
        'currentLang': 'हिंदी',
        'appTitle': 'कृषि पहचान प्रणाली',
        'chooseText': 'आप क्या विश्लेषण करना चाहते हैं:',
        'soilDetectionTitle': 'मिट्टी की पहचान',
        'soilDetectionDesc': 'भूमि प्रकार, जलवायु का विश्लेषण करें और फसल सुझाव प्राप्त करें',
        'plantHealthTitle': 'पौधे का स्वास्थ्य',
        'plantHealthDesc': 'पौधे के स्वास्थ्य की जांच करें और उपचार की सिफारिशें प्राप्त करें',
        'backBtn': 'वापस',
        'soilTitle': 'मिट्टी की पहचान',
        'uploadLandLabel': 'भूमि की छवि अपलोड करें:',
        'analyzeBtn': 'मिट्टी का विश्लेषण करें',
        'resultsTitle': 'विश्लेषण परिणाम:',
        'landTypeLabel': 'भूमि प्रकार:',
        'climateLabel': 'जलवायु:',
        'waterLabel': 'पानी की सुविधा:',
        'phLabel': 'मिट्टी का पीएच:',
        'yieldLabel': 'अनुमानित उपज:',
        'suitabilityLabel': 'उपयुक्तता:',
        'suggestedCropsLabel': 'सुझाई गई फसलें:',
        'plantTitle': 'पौधे के स्वास्थ्य की जांच',
        'uploadPlantLabel': 'पौधे की छवि अपलोड करें:',
        'checkHealthBtn': 'पौधे का स्वास्थ्य जांचें',
        'healthResultsTitle': 'स्वास्थ्य रिपोर्ट:',
        'healthStatusLabel': 'स्वास्थ्य स्थिति:',
        'healthScoreLabel': 'स्वास्थ्य स्कोर:',
        'detectedIssuesLabel': 'पाई गई समस्याएं:',
        'recommendationsLabel': 'सिफारिशें:',
        'chatTitle': 'एआई सहायक',
        'welcomeMessage': 'नमस्ते! मैं आज आपकी कैसे मदद कर सकता हूं?',
        'sendBtn': 'भेजें'
    },
    'kn': {
        'changeLangBtn': 'ಭಾಷೆ ಬದಲಾಯಿಸಿ',
        'currentLang': 'ಕನ್ನಡ',
        'appTitle': 'ಕೃಷಿ ಪತ್ತೆ ವ್ಯವಸ್ಥೆ',
        'chooseText': 'ನೀವು ಏನನ್ನು ವಿಶ್ಲೇಷಿಸಲು ಬಯಸುತ್ತೀರಿ:',
        'soilDetectionTitle': 'ಮಣ್ಣಿನ ಪತ್ತೆ',
        'soilDetectionDesc': 'ಭೂಮಿ ಪ್ರಕಾರ, ಹವಾಮಾನವನ್ನು ವಿಶ್ಲೇಷಿಸಿ ಮತ್ತು ಬೆಳೆ ಸಲಹೆಗಳನ್ನು ಪಡೆಯಿರಿ',
        'plantHealthTitle': 'ಸಸ್ಯ ಆರೋಗ್ಯ',
        'plantHealthDesc': 'ಸಸ್ಯ ಆರೋಗ್ಯವನ್ನು ಪರಿಶೀಲಿಸಿ ಮತ್ತು ಚಿಕಿತ್ಸಾ ಶಿಫಾರಸುಗಳನ್ನು ಪಡೆಯಿರಿ',
        'backBtn': 'ಹಿಂದೆ',
        'soilTitle': 'ಮಣ್ಣಿನ ಪತ್ತೆ',
        'uploadLandLabel': 'ಭೂಮಿಯ ಚಿತ್ರವನ್ನು ಅಪ್‌ಲೋಡ್ ಮಾಡಿ:',
        'analyzeBtn': 'ಮಣ್ಣನ್ನು ವಿಶ್ಲೇಷಿಸಿ',
        'resultsTitle': 'ವಿಶ್ಲೇಷಣೆ ಫಲಿತಾಂಶಗಳು:',
        'landTypeLabel': 'ಭೂಮಿ ಪ್ರಕಾರ:',
        'climateLabel': 'ಹವಾಮಾನ:',
        'waterLabel': 'ನೀರಿನ ಸೌಲಭ್ಯ:',
        'phLabel': 'ಮಣ್ಣಿನ pH:',
        'yieldLabel': 'ಅಂದಾಜು ಇಳುವರಿ:',
        'suitabilityLabel': 'ಸೂಕ್ತತೆ:',
        'suggestedCropsLabel': 'ಸೂಚಿಸಲಾದ ಬೆಳೆಗಳು:',
        'plantTitle': 'ಸಸ್ಯ ಆರೋಗ್ಯ ಪರೀಕ್ಷೆ',
        'uploadPlantLabel': 'ಸಸ್ಯದ ಚಿತ್ರವನ್ನು ಅಪ್‌ಲೋಡ್ ಮಾಡಿ:',
        'checkHealthBtn': 'ಸಸ್ಯ ಆರೋಗ್ಯವನ್ನು ಪರಿಶೀಲಿಸಿ',
        'healthResultsTitle': 'ಆರೋಗ್ಯ ವರದಿ:',
        'healthStatusLabel': 'ಆರೋಗ್ಯ ಸ್ಥಿತಿ:',
        'healthScoreLabel': 'ಆರೋಗ್ಯ ಅಂಕ:',
        'detectedIssuesLabel': 'ಪತ್ತೆಯಾದ ಸಮಸ್ಯೆಗಳು:',
        'recommendationsLabel': 'ಶಿಫಾರಸುಗಳು:',
        'chatTitle': 'AI ಸಹಾಯಕ',
        'welcomeMessage': 'ನಮಸ್ಕಾರ! ಇಂದು ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಬಹುದು?',
        'sendBtn': 'ಕಳುಹಿಸಿ'
    }
}

# Translated data values
SOIL_DATA = {
    'en': {
        'land_types': ['Clayey', 'Sandy', 'Loamy', 'Black Soil', 'Red Soil'],
        'climates': ['Tropical', 'Subtropical', 'Temperate', 'Arid', 'Semi-Arid'],
        'water_facilities': ['Good', 'Moderate', 'Limited', 'Excellent'],
        'crops': ['Rice, Wheat, Sugarcane', 'Cotton, Maize, Pulses', 'Vegetables, Fruits', 'Paddy, Coconut'],
        'yield_unit': 'kg/hectare',
        'suitable': 'Suitable'
    },
    'hi': {
        'land_types': ['मिट्टी', 'रेतीली', 'दोमट', 'काली मिट्टी', 'लाल मिट्टी'],
        'climates': ['उष्णकटिबंधीय', 'उपोष्णकटिबंधीय', 'समशीतोष्ण', 'शुष्क', 'अर्ध-शुष्क'],
        'water_facilities': ['अच्छी', 'मध्यम', 'सीमित', 'उत्कृष्ट'],
        'crops': ['चावल, गेहूं, गन्ना', 'कपास, मक्का, दालें', 'सब्जियां, फल', 'धान, नारियल'],
        'yield_unit': 'किलो/हेक्टेयर',
        'suitable': 'उपयुक्त'
    },
    'kn': {
        'land_types': ['ಜೇಡಿಮಣ್ಣು', 'ಮರಳು', 'ಲೋಮ್', 'ಕಪ್ಪು ಮಣ್ಣು', 'ಕೆಂಪು ಮಣ್ಣು'],
        'climates': ['ಉಷ್ಣವಲಯ', 'ಉಪೋಷ್ಣವಲಯ', 'ಸಮಶೀತೋಷ್ಣ', 'ಶುಷ್ಕ', 'ಅರೆ-ಶುಷ್ಕ'],
        'water_facilities': ['ಉತ್ತಮ', 'ಮಧ್ಯಮ', 'ಸೀಮಿತ', 'ಅತ್ಯುತ್ತಮ'],
        'crops': ['ಅಕ್ಕಿ, ಗೋಧಿ, ಕಬ್ಬು', 'ಹತ್ತಿ, ಜೋಳ, ದಾಳಿ', 'ತರಕಾರಿಗಳು, ಹಣ್ಣುಗಳು', 'ಭತ್ತ, ತೆಂಗು'],
        'yield_unit': 'ಕೆಜಿ/ಹೆಕ್ಟೇರ್',
        'suitable': 'ಸೂಕ್ತ'
    }
}

PLANT_DATA = {
    'en': {
        'health_statuses': ['Healthy', 'Mild Disease', 'Moderate Disease', 'Needs Attention'],
        'issues': [
            'No major issues detected',
            'Early Blight detected',
            'Leaf Spot observed',
            'Nutrient deficiency detected',
            'Pest infestation signs'
        ],
        'recommendations': [
            'Continue regular watering and monitoring',
            'Apply organic fungicide and improve drainage',
            'Remove affected leaves and apply neem oil',
            'Add balanced fertilizer and improve soil nutrition',
            'Use organic pest control methods'
        ]
    },
    'hi': {
        'health_statuses': ['स्वस्थ', 'हल्की बीमारी', 'मध्यम बीमारी', 'ध्यान चाहिए'],
        'issues': [
            'कोई बड़ी समस्या नहीं मिली',
            'प्रारंभिक झुलसा रोग का पता चला',
            'पत्ती के धब्बे देखे गए',
            'पोषक तत्व की कमी का पता चला',
            'कीट संक्रमण के संकेत'
        ],
        'recommendations': [
            'नियमित पानी देना और निगरानी जारी रखें',
            'जैविक कवकनाशी लगाएं और जल निकासी में सुधार करें',
            'प्रभावित पत्तियों को हटाएं और नीम का तेल लगाएं',
            'संतुलित उर्वरक डालें और मिट्टी के पोषण में सुधार करें',
            'जैविक कीट नियंत्रण विधियों का उपयोग करें'
        ]
    },
    'kn': {
        'health_statuses': ['ಆರೋಗ್ಯಕರ', 'ಸೌಮ್ಯ ರೋಗ', 'ಮಧ್ಯಮ ರೋಗ', 'ಗಮನ ಬೇಕು'],
        'issues': [
            'ಯಾವುದೇ ಪ್ರಮುಖ ಸಮಸ್ಯೆಗಳು ಪತ್ತೆಯಾಗಿಲ್ಲ',
            'ಆರಂಭಿಕ ಬ್ಲೈಟ್ ಪತ್ತೆಯಾಗಿದೆ',
            'ಎಲೆ ಚುಕ್ಕೆ ಗಮನಿಸಲಾಗಿದೆ',
            'ಪೋಷಕಾಂಶದ ಕೊರತೆ ಪತ್ತೆಯಾಗಿದೆ',
            'ಕೀಟ ಮುತ್ತಿಕೊಳ್ಳುವಿಕೆಯ ಚಿಹ್ನೆಗಳು'
        ],
        'recommendations': [
            'ನಿಯಮಿತ ನೀರುಹಾಕುವಿಕೆ ಮತ್ತು ಮೇಲ್ವಿಚಾರಣೆ ಮುಂದುವರಿಸಿ',
            'ಸಾವಯವ ಶಿಲೀಂಧ್ರನಾಶಕವನ್ನು ಅನ್ವಯಿಸಿ ಮತ್ತು ಒಳಚರಂಡಿ ಸುಧಾರಿಸಿ',
            'ಪೀಡಿತ ಎಲೆಗಳನ್ನು ತೆಗೆದುಹಾಕಿ ಮತ್ತು ಬೇವಿನ ಎಣ್ಣೆ ಹಚ್ಚಿ',
            'ಸಮತೋಲಿತ ರಸಗೊಬ್ಬರ ಸೇರಿಸಿ ಮತ್ತು ಮಣ್ಣಿನ ಪೋಷಣೆ ಸುಧಾರಿಸಿ',
            'ಸಾವಯವ ಕೀಟ ನಿಯಂತ್ರಣ ವಿಧಾನಗಳನ್ನು ಬಳಸಿ'
        ]
    }
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get-translations/<lang>')
def get_translations(lang):
    return jsonify(TRANSLATIONS.get(lang, TRANSLATIONS['en']))

@app.route('/predict-details-from-image', methods=['POST'])
def predict_details():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    
    # Get language from request or default to English
    lang = request.form.get('language', 'en')
    soil_data = SOIL_DATA.get(lang, SOIL_DATA['en'])
    
    prediction = {
        'land_type': random.choice(soil_data['land_types']),
        'climate': random.choice(soil_data['climates']),
        'water_facility': random.choice(soil_data['water_facilities']),
        'ph': f"{random.uniform(5.5, 8.5):.1f}",
        'yield': f"{random.randint(2000, 5000)} {soil_data['yield_unit']}",
        'suitability': f"{random.randint(70, 95)}% {soil_data['suitable']}",
        'suggested_crops': random.choice(soil_data['crops'])
    }
    
    return jsonify(prediction)

@app.route('/model-status')
def model_status():
    return jsonify({
        'model_loaded': plant_interpreter is not None,
        'load_error': plant_model_load_error,
        'model_dir': MODEL_DIR,
        'tflite_file_present': os.path.exists(TFLITE_PATH),
        'class_names_file_present': os.path.exists(CLASS_NAMES_PATH),
        'class_names': plant_class_names,
    })

@app.route('/predict-plant-health', methods=['POST'])
def predict_plant_health():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    # Get language from request or default to English
    lang = request.form.get('language', 'en')
    plant_data = PLANT_DATA.get(lang, PLANT_DATA['en'])

    image_file = request.files['image']
    result = None
    try:
        result = run_plant_inference(image_file.read())
    except Exception as e:
        print('[plant_health] Inference error, falling back to simulated result:', e)
        result = None

    if result is None:
        # No trained model available yet (or inference failed) - old simulated behavior
        health_data = {
            'health_status': random.choice(plant_data['health_statuses']),
            'health_score': f"{random.randint(60, 98)}%",
            'detected_issues': random.choice(plant_data['issues']),
            'recommendations': random.choice(plant_data['recommendations']),
        }
        return jsonify(health_data)

    crop, condition, confidence = result
    condition_lower = condition.lower()
    is_healthy = 'healthy' in condition_lower
    bucket = classify_condition(condition_lower)

    if is_healthy:
        status_idx = 0
    elif confidence > 0.85:
        status_idx = 3  # Needs Attention
    elif confidence > 0.6:
        status_idx = 2  # Moderate Disease
    else:
        status_idx = 1  # Mild Disease (model itself is not very confident)

    if is_healthy:
        issue_text = plant_data['issues'][0]
    else:
        # crop/condition names come from the model's English class labels;
        # full translation of all 38 class names into hi/kn is not yet built,
        # so we show the model's finding plus a translated recommendation.
        label = f"{crop} - {condition}" if crop else condition
        issue_text = f"{label} detected" if lang == 'en' else label

    health_data = {
        'health_status': plant_data['health_statuses'][status_idx],
        'health_score': f"{round(confidence * 100)}%",
        'detected_issues': issue_text,
        'recommendations': plant_data['recommendations'][bucket],
    }
    return jsonify(health_data)


@app.route('/chatbot', methods=['POST'])
def chatbot():
    data = request.json
    message = data.get('message', '')
    language = data.get('language', 'en')
    responses = {
        'en': {
            'default': 'I can help you with crop suggestions, soil analysis, and plant health questions. What would you like to know?',
            'soil': 'Upload a land image in the Soil Detection section to analyze land type, climate, pH, and get crop suggestions.',
            'crop': 'I can suggest crops based on your soil type and climate. Please analyze your land first.',
            'disease': 'Upload a plant image for disease detection and treatment recommendations.',
            'scan': 'Yes, you can scan another plant. Use the back button in the top-left corner to return to the main menu.'
        },
        'hi': {
            'default': 'मैं फसल सुझाव, मिट्टी विश्लेषण और पौधे के स्वास्थ्य प्रश्नों में आपकी मदद कर सकता हूं। आप क्या जानना चाहेंगे?',
            'soil': 'भूमि प्रकार, जलवायु, pH का विश्लेषण करने और फसल सुझाव पाने के लिए मिट्टी पहचान अनुभाग में भूमि की छवि अपलोड करें।',
            'crop': 'मैं आपकी मिट्टी के प्रकार और जलवायु के आधार पर फसलों का सुझाव दे सकता हूं। कृपया पहले अपनी भूमि का विश्लेषण करें।',
            'disease': 'रोग का पता लगाने और उपचार की सिफारिशों के लिए पौधे की छवि अपलोड करें।',
            'scan': 'हाँ, आप कर सकते हैं। मुख्य मेनू पर वापस जाने के लिए ऊपर बाएँ कोने में बैक बटन का उपयोग करें।'
        },
        'kn': {
            'default': 'ನಾನು ಬೆಳೆ ಸಲಹೆಗಳು, ಮಣ್ಣಿನ ವಿಶ್ಲೇಷಣೆ ಮತ್ತು ಸಸ್ಯ ಆರೋಗ್ಯ ಪ್ರಶ್ನೆಗಳಲ್ಲಿ ನಿಮಗೆ ಸಹಾಯ ಮಾಡಬಹುದು.',
            'soil': 'ಭೂಮಿ ಪ್ರಕಾರ, ಹವಾಮಾನ, pH ವಿಶ್ಲೇಷಿಸಲು ಮತ್ತು ಬೆಳೆ ಸಲಹೆಗಳನ್ನು ಪಡೆಯಲು ಮಣ್ಣಿನ ಪತ್ತೆ ವಿಭಾಗದಲ್ಲಿ ಭೂಮಿಯ ಚಿತ್ರವನ್ನು ಅಪ್‌ಲೋಡ್ ಮಾಡಿ.',
            'crop': 'ನಿಮ್ಮ ಮಣ್ಣಿನ ಪ್ರಕಾರ ಮತ್ತು ಹವಾಮಾನದ ಆಧಾರದ ಮೇಲೆ ನಾನು ಬೆಳೆಗಳನ್ನು ಸೂಚಿಸಬಹುದು. ದಯವಿಟ್ಟು ಮೊದಲು ನಿಮ್ಮ ಭೂಮಿಯನ್ನು ವಿಶ್ಲೇಷಿಸಿ.',
            'disease': 'ರೋಗ ಪತ್ತೆ ಮತ್ತು ಚಿಕಿತ್ಸಾ ಶಿಫಾರಸುಗಳಿಗಾಗಿ ಸಸ್ಯದ ಚಿತ್ರವನ್ನು ಅಪ್‌ಲೋಡ್ ಮಾಡಿ.',
            'scan': 'ಹೌದು, ನೀವು ಮತ್ತೊಂದು ಸಸ್ಯವನ್ನು ಸ್ಕ್ಯಾನ್ ಮಾಡಬಹುದು. ಮುಖ್ಯ ಮೆನುಗೆ ಹಿಂತಿರುಗಲು ಮೇಲಿನ ಎಡ ಮೂಲೆಯಲ್ಲಿರುವ ಹಿಂದೆ ಬಟನ್ ಬಳಸಿ.'
        }
    }
    
    message_lower = message.lower()
    lang_responses = responses.get(language, responses['en'])
    
    if 'scan' in message_lower or 'another plant' in message_lower:
        response_text = lang_responses['scan']
    elif 'soil' in message_lower or 'मिट्टी' in message_lower or 'ಮಣ್ಣು' in message_lower:
        response_text = lang_responses['soil']
    elif 'crop' in message_lower or 'फसल' in message_lower or 'ಬೆಳೆ' in message_lower:
        response_text = lang_responses['crop']
    elif 'disease' in message_lower or 'रोग' in message_lower or 'ರೋಗ' in message_lower or 'plant' in message_lower:
        response_text = lang_responses['disease']
    else:
        response_text = lang_responses['default']
    
    return jsonify({'response': response_text})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug, host='0.0.0.0', port=port)