"""
Trains a plant-health image classifier using transfer learning on MobileNetV2.

This script works on this small demo subset (480 images / 6 classes) AND
on the full PlantVillage dataset (38 classes / ~54k images) if you point
DATA_DIR at the full download - no code changes needed, just more data
and more epochs (see train_full_colab.py for the scaled-up version).
"""
import os
import json
import tensorflow as tf
from tensorflow.keras import layers, models

DATA_DIR = "data"
IMG_SIZE = (160, 160)   # small + fast; MobileNetV2's native efficient size
BATCH_SIZE = 16
EPOCHS = 12
SEED = 42

def build_datasets():
    train_ds = tf.keras.utils.image_dataset_from_directory(
        DATA_DIR, validation_split=0.2, subset="training", seed=SEED,
        image_size=IMG_SIZE, batch_size=BATCH_SIZE, label_mode="categorical",
    )
    val_ds = tf.keras.utils.image_dataset_from_directory(
        DATA_DIR, validation_split=0.2, subset="validation", seed=SEED,
        image_size=IMG_SIZE, batch_size=BATCH_SIZE, label_mode="categorical",
    )
    class_names = train_ds.class_names
    AUTOTUNE = tf.data.AUTOTUNE
    train_ds = train_ds.cache().shuffle(200).prefetch(AUTOTUNE)
    val_ds = val_ds.cache().prefetch(AUTOTUNE)
    return train_ds, val_ds, class_names

def build_model(num_classes):
    # NOTE: ImageNet-pretrained MobileNetV2 weights are downloaded from
    # storage.googleapis.com, which this sandbox's network can't reach.
    # This sandbox therefore trains a compact CNN from scratch on the demo
    # subset below. train_full_colab.py (given separately) uses
    # weights="imagenet" and will get meaningfully higher accuracy when you
    # run it on Colab/Kaggle/your own machine, which has normal internet access.
    data_augmentation = tf.keras.Sequential([
        layers.RandomFlip("horizontal"),
        layers.RandomRotation(0.08),
        layers.RandomZoom(0.1),
    ])

    inputs = tf.keras.Input(shape=IMG_SIZE + (3,))
    x = data_augmentation(inputs)
    x = layers.Rescaling(1.0 / 255)(x)

    for filters in (32, 64, 128, 128):
        x = layers.Conv2D(filters, 3, padding="same", activation="relu")(x)
        x = layers.BatchNormalization()(x)
        x = layers.MaxPooling2D()(x)

    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.4)(x)
    x = layers.Dense(128, activation="relu")(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(num_classes, activation="softmax")(x)
    model = models.Model(inputs, outputs)

    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model

def main():
    train_ds, val_ds, class_names = build_datasets()
    print("Classes:", class_names)

    model = build_model(len(class_names))
    model.summary()

    callbacks = [
        tf.keras.callbacks.EarlyStopping(patience=4, restore_best_weights=True, monitor="val_accuracy"),
    ]

    history = model.fit(train_ds, validation_data=val_ds, epochs=EPOCHS, callbacks=callbacks)

    val_loss, val_acc = model.evaluate(val_ds)
    print(f"Final validation accuracy: {val_acc:.3f}")

    os.makedirs("model_out", exist_ok=True)
    model.save("model_out/plant_health_model.keras")
    with open("model_out/class_names.json", "w") as f:
        json.dump(class_names, f, indent=2)

    # Also export a lightweight TFLite version for cheap deployment (e.g. Render free tier)
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    tflite_model = converter.convert()
    with open("model_out/plant_health_model.tflite", "wb") as f:
        f.write(tflite_model)

    print("Saved model_out/plant_health_model.keras")
    print("Saved model_out/plant_health_model.tflite")
    print("Saved model_out/class_names.json")

if __name__ == "__main__":
    main()
