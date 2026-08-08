# Plant Health Detector — what changed and what to do next

## What's in this drop

| File | What it is |
|---|---|
| `app.py` | Your Flask app, updated. `/predict-plant-health` now runs real model inference instead of `random.choice()`. Falls back to the old simulated behavior automatically if no model file is found, so the app never breaks. |
| `models/plant_health_model.tflite` | A **demo** model — trained here as a proof of concept. See accuracy warning below. |
| `models/class_names.json` | The class labels the demo model was trained on. |
| `requirements.txt` | Updated with `numpy`, `Pillow`, `tflite-runtime` (a small ~2.4MB inference-only package — much lighter than full TensorFlow, good for Render's free tier). |
| `train.py` | The script that trained the demo model. Only useful for reference/tinkering in a sandbox with no GPU. |
| `train_full_colab.py` | **The script you actually want to run** to get a real, usable model. See below. |

## ⚠️ Important: the included demo model is NOT production-ready

It was trained from scratch (no pretrained weights — see why below) on only 480 images across 6 classes, for a quick end-to-end proof that the pipeline works. Validation accuracy: **~37.5%**. In testing it misclassified a scabbed apple leaf and a blighted tomato leaf as "healthy." Don't ship this model to real users. It exists so you can confirm the plumbing (upload → inference → JSON → UI) works today.

Why not pretrained weights? ImageNet weights for MobileNetV2 are normally auto-downloaded from `storage.googleapis.com`, which the sandbox that built this couldn't reach. Colab has normal internet access, so this isn't a problem there.

## Get a real model: run `train_full_colab.py` on Google Colab (free)

1. Go to https://colab.research.google.com/ → New notebook.
2. **Runtime → Change runtime type → Hardware accelerator → GPU** (T4 is fine, free tier).
3. In a cell:
   ```
   !git clone https://github.com/spMohanty/PlantVillage-Dataset.git
   ```
4. Upload `train_full_colab.py` to the Colab file browser (left sidebar → folder icon → upload), or paste its contents into a cell.
5. Run:
   ```
   !python train_full_colab.py
   ```
   Takes roughly 30–60 minutes on a free T4 GPU for all 38 classes (~54,000 images). It trains a classifier head first, then fine-tunes the top layers of MobileNetV2 — real transfer learning, not from-scratch training, so expect meaningfully higher accuracy than the demo (well-tuned versions of this exact approach on PlantVillage typically land in the 90%+ range, though your exact number will depend on epochs/tuning).
6. When it finishes, download from the Colab file browser:
   - `model_out/plant_health_model.tflite`
   - `model_out/class_names.json`
7. Replace the files in your repo's `models/` folder with these, commit, push, and Render will redeploy automatically.

That's the entire swap — `app.py` doesn't need to change again, it already loads whatever is in `models/`.

## Known scope limits, so you can plan around them

- **Translations for detected diseases**: `detected_issues` for non-English languages currently shows the disease name pulled straight from the model's English class label (e.g. "Tomato - Early blight detected"), not a fully localized sentence. `recommendations` and `health_status` *are* fully translated (hi/kn), reusing your existing translation dictionaries mapped by disease category (fungal/spot/pest/etc.). Full translation of all 38 disease names into Hindi/Kannada would be a follow-up if you want it.
- **Soil Detection is still simulated** (`random.choice()`) — we agreed to do Plant Health first. Land type (from soil color/texture) is learnable the same way; climate/pH/water/yield are not reliably inferable from a photo and should come from a lookup table keyed to predicted land type instead, not from image predictions, when you're ready to tackle that.
- **Health score** is the model's raw softmax confidence for its top prediction, not a calibrated "how healthy is this plant" percentage — worth knowing if you display it prominently.
