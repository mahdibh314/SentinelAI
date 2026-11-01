"""Étape 2a : vérifier PyTorch, CUDA et le GPU."""
import torch
import ultralytics

print("PyTorch :", torch.__version__)
print("Ultralytics :", ultralytics.__version__)
print("CUDA disponible :", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU :", torch.cuda.get_device_name(0))
