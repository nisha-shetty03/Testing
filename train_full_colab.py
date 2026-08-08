"""
PRODUCTION training script - run this on Google Colab (free GPU) or Kaggle
Notebooks, NOT in a constrained sandbox. Uses real ImageNet transfer learning
on the full PlantVillage dataset (38 classes, ~54k images) for much higher
accuracy than the small demo trained in the dev sandbox.

===================== HOW TO RUN ON GOOGLE COLAB =====================
1. Go to https://colab.research.google.com/ -> New notebook
2. Runtime -> Change runtime type -> select GPU (T4 is fine, free tier)
3. In a cell, run:
     !git clone https://github.com/spMohanty/PlantVillage-Dataset.git
4. Upload this file (train_full_colab.py) to the Colab file browser, or paste
   its contents into a cell.
5. Run: !python train_full_colab.py
   (takes ~30-60 min on a free T4 GPU for the full 38-class dataset)
6. Download model_out/plant_health_model.keras (or the .tflite version) from
   the Colab file browser.
7. Copy it into your Crop_yield_detector repo (see app.py changes) and
   redeploy on Render.
========================================================================
"""
import os
import json
import tensorflow as tf
from tensorflow.keras import layers, models

DATA_DIR = "PlantVillage-Dataset/raw/color"  # from the git clone above
IMG_SIZE = (160, 160)
BATCH_SIZE = 32
INITIAL_EPOCHS = 10
FINE_TUNE_EPOCHS = 8
SEED = 42

def build_datasets():
    train_ds = tf.keras.utils.image_dataset_from_directory(
        DATA_DIR, validation_split=0.15, subset="training", seed=SEED,
        image_size=IMG_SIZE, batch_size=BATCH_SIZE, label_mode="categorical",
    )
    val_ds = tf.keras.utils.image_dataset_from_directory(
        DATA_DIR, validation_split=0.15, subset="validation", seed=SEED,
        image_size=IMG_SIZE, batch_size=BATCH_SIZE, label_mode="categorical",
    )
    class_names = train_ds.class_names
    AUTOTUNE = tf.data.AUTOTUNE
    train_ds = train_ds.cache().shuffle(1000).prefetch(AUTOTUNE)
    val_ds = val_ds.cache().prefetch(AUTOTUNE)
    return train_ds, val_ds, class_names

def build_model(num_classes):
    base = tf.keras.applications.MobileNetV2(
        input_shape=IMG_SIZE + (3,), include_top=False, weights="imagenet"
    )
    base.trainable = False

    data_augmentation = tf.keras.Sequential([
        layers.RandomFlip("horizontal"),
        layers.RandomRotation(0.08),
        layers.RandomZoom(0.1),
        layers.RandomContrast(0.1),
    ])

    inputs = tf.keras.Input(shape=IMG_SIZE + (3,))
    x = data_augmentation(inputs)
    x = tf.keras.applications.mobilenet_v2.preprocess_input(x)
    x = base(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(num_classes, activation="softmax")(x)
    model = models.Model(inputs, outputs)

    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model, base

def main():
    train_ds, val_ds, class_names = build_datasets()
    print(f"Classes ({len(class_names)}):", class_names)

    model, base = build_model(len(class_names))
    model.summary()

    callbacks = [
        tf.keras.callbacks.EarlyStopping(patience=3, restore_best_weights=True, monitor="val_accuracy"),
        tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=2),
    ]

    print("=== Stage 1: training classifier head (base frozen) ===")
    model.fit(train_ds, validation_data=val_ds, epochs=INITIAL_EPOCHS, callbacks=callbacks)

    print("=== Stage 2: fine-tuning top layers of MobileNetV2 ===")
    base.trainable = True
    fine_tune_at = len(base.layers) - 40
    for layer in base.layers[:fine_tune_at]:
        layer.trainable = False

    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-5),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )
    model.fit(train_ds, validation_data=val_ds, epochs=FINE_TUNE_EPOCHS, callbacks=callbacks)

    val_loss, val_acc = model.evaluate(val_ds)
    print(f"Final validation accuracy: {val_acc:.3f}")

    os.makedirs("model_out", exist_ok=True)
    model.save("model_out/plant_health_model.keras")
    with open("model_out/class_names.json", "w") as f:
        json.dump(class_names, f, indent=2)

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    tflite_model = converter.convert()
    with open("model_out/plant_health_model.tflite", "wb") as f:
        f.write(tflite_model)

    print("Saved model_out/plant_health_model.keras")
    print("Saved model_out/plant_health_model.tflite  <- use this one for Render deployment (smaller, no full TF needed)")
    print("Saved model_out/class_names.json")

if __name__ == "__main__":
    main()
