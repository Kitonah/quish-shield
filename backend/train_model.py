"""
+======================================================================+
|  QuiShield -- train_model.py                                          |
|                                                                       |
|  WHAT THIS FILE DOES (in plain English):                              |
|  Takes the screenshots collected by collect_data.py and "teaches"     |
|  a pre-trained AI model (MobileNetV2) to recognize which brand a     |
|  webpage belongs to.                                                  |
|                                                                       |
|  The result is a file called "brand_model.pth" which is the          |
|  "trained brain" that visual_matcher.py will use.                    |
|                                                                       |
|  HOW TO RUN:                                                          |
|    python train_model.py                                              |
|                                                                       |
|  Prerequisites:                                                       |
|    pip install torch torchvision Pillow                               |
|    python collect_data.py   (to generate training data first)        |
+======================================================================+
"""

import os
import sys
import json
import copy
import time

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, transforms, models


# ---- Configuration -----------------------------------------------------------

# Where the training images live (created by collect_data.py)
DATA_DIR = os.path.join(os.path.dirname(__file__), "training_data")

# Where to save the trained model
MODEL_PATH = os.path.join(os.path.dirname(__file__), "brand_model.pth")

# Where to save the class-name mapping (so we know which index = which brand)
LABELS_PATH = os.path.join(os.path.dirname(__file__), "brand_labels.json")

# Training settings (these work well for fine-tuning on a laptop)
BATCH_SIZE = 16        # How many images to process at once
NUM_EPOCHS = 12        # How many times to go through all the data
LEARNING_RATE = 0.001  # How fast the model learns (smaller = more careful)
TRAIN_SPLIT = 0.8      # 80% for training, 20% for testing

# Image size that MobileNetV2 expects
IMG_SIZE = 224


# ---- Data preparation --------------------------------------------------------

def get_data_transforms():
    """
    Defines how images are preprocessed before being fed to the model.

    Training transforms include random augmentations (flips, color changes)
    to make the model more robust. Think of it like showing the student
    slightly different versions of each flashcard.

    Validation transforms are simpler -- just resize and normalize.
    """
    train_transforms = transforms.Compose([
        transforms.Resize((IMG_SIZE + 32, IMG_SIZE + 32)),
        transforms.RandomCrop(IMG_SIZE),
        transforms.RandomHorizontalFlip(p=0.3),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.1),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],  # ImageNet standards
            std=[0.229, 0.224, 0.225],
        ),
    ])

    val_transforms = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        ),
    ])

    return train_transforms, val_transforms


def load_dataset():
    """
    Loads all images from training_data/ using PyTorch's ImageFolder.
    ImageFolder automatically uses subfolder names as class labels.
    """
    if not os.path.exists(DATA_DIR):
        print(f"ERROR: Data folder not found at '{DATA_DIR}'")
        print("Run 'python collect_data.py' first to collect training images.")
        sys.exit(1)

    # Check we have enough data
    subfolders = [
        d for d in os.listdir(DATA_DIR)
        if os.path.isdir(os.path.join(DATA_DIR, d))
    ]

    if len(subfolders) < 2:
        print(f"ERROR: Need at least 2 brand folders, found {len(subfolders)}")
        sys.exit(1)

    print(f"\nFound {len(subfolders)} brand categories:")
    for sf in sorted(subfolders):
        count = len([
            f for f in os.listdir(os.path.join(DATA_DIR, sf))
            if f.lower().endswith(('.png', '.jpg', '.jpeg'))
        ])
        print(f"  {sf:15s} -> {count} images")

    # We load the full dataset with training transforms first,
    # then split into train/val sets.
    train_tf, val_tf = get_data_transforms()

    full_dataset = datasets.ImageFolder(DATA_DIR, transform=train_tf)

    # Split into training and validation
    total = len(full_dataset)
    train_size = int(total * TRAIN_SPLIT)
    val_size = total - train_size

    train_dataset, val_dataset = random_split(full_dataset, [train_size, val_size])

    # Override the validation subset's transform
    # (We can't directly set transform on a Subset, so we wrap it)
    val_dataset.dataset = copy.copy(full_dataset)
    val_dataset.dataset.transform = val_tf

    print(f"\nDataset split: {train_size} training + {val_size} validation = {total} total")

    # Save the class labels mapping
    class_names = full_dataset.classes  # e.g., ['amazon', 'google', 'hdfc', ...]
    with open(LABELS_PATH, 'w') as f:
        json.dump(class_names, f, indent=2)
    print(f"Class labels saved to: {LABELS_PATH}")
    print(f"Classes: {class_names}")

    return train_dataset, val_dataset, class_names


# ---- Model setup -------------------------------------------------------------

def create_model(num_classes: int):
    """
    Loads a pre-trained MobileNetV2 and replaces the final layer
    so it classifies into our brand categories.

    Think of it like hiring an experienced artist and asking them
    to learn to draw 9 new specific things.
    """
    # Load MobileNetV2 with pre-trained weights
    model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)

    # Freeze most layers (don't re-train the foundation)
    # We only unfreeze the last few layers + the classifier.
    for param in model.features[:-4].parameters():
        param.requires_grad = False

    # Replace the final classifier layer
    # Original: 1280 -> 1000 (ImageNet classes)
    # Ours:     1280 -> num_classes (our brand count)
    num_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.3),
        nn.Linear(num_features, 256),
        nn.ReLU(),
        nn.Dropout(p=0.2),
        nn.Linear(256, num_classes),
    )

    return model


# ---- Training loop -----------------------------------------------------------

def train_model(model, train_loader, val_loader, device):
    """
    The actual training loop. Goes through the data NUM_EPOCHS times,
    adjusting the model's weights each time to get better at predicting.
    """
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=LEARNING_RATE,
    )

    # Learning rate scheduler -- reduces LR when progress stalls
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.5)

    best_acc = 0.0
    best_model_weights = copy.deepcopy(model.state_dict())

    print(f"\nStarting training on: {device}")
    print(f"Epochs: {NUM_EPOCHS}  |  Batch size: {BATCH_SIZE}")
    print("-" * 55)

    for epoch in range(NUM_EPOCHS):
        epoch_start = time.time()

        # ---- Training phase ----
        model.train()
        running_loss = 0.0
        running_correct = 0
        running_total = 0

        for inputs, labels in train_loader:
            inputs, labels = inputs.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            _, predicted = torch.max(outputs, 1)
            running_loss += loss.item() * inputs.size(0)
            running_correct += (predicted == labels).sum().item()
            running_total += labels.size(0)

        train_loss = running_loss / running_total
        train_acc = running_correct / running_total

        # ---- Validation phase ----
        model.eval()
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                outputs = model(inputs)
                _, predicted = torch.max(outputs, 1)
                val_correct += (predicted == labels).sum().item()
                val_total += labels.size(0)

        val_acc = val_correct / val_total if val_total > 0 else 0.0

        elapsed = time.time() - epoch_start

        print(
            f"  Epoch {epoch+1:2d}/{NUM_EPOCHS}"
            f"  |  Train Loss: {train_loss:.4f}"
            f"  |  Train Acc: {train_acc:.1%}"
            f"  |  Val Acc: {val_acc:.1%}"
            f"  |  {elapsed:.1f}s"
        )

        # Save the best model
        if val_acc > best_acc:
            best_acc = val_acc
            best_model_weights = copy.deepcopy(model.state_dict())

        scheduler.step()

    print("-" * 55)
    print(f"  Best validation accuracy: {best_acc:.1%}")

    # Load the best weights back
    model.load_state_dict(best_model_weights)
    return model, best_acc


# ---- Entry point -------------------------------------------------------------

def main():
    print("\n" + "=" * 55)
    print("  [QuiShield] Model Trainer")
    print("  Training MobileNetV2 to recognize brand pages")
    print("=" * 55)

    # Detect GPU or CPU
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cuda":
        print(f"\n  GPU detected: {torch.cuda.get_device_name(0)}")
    else:
        print("\n  No GPU detected, using CPU (this is fine, just slower)")

    # Load data
    train_dataset, val_dataset, class_names = load_dataset()

    train_loader = DataLoader(
        train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=0
    )
    val_loader = DataLoader(
        val_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0
    )

    # Create model
    num_classes = len(class_names)
    model = create_model(num_classes)
    model = model.to(device)

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"\n  Model parameters: {total:,} total, {trainable:,} trainable")

    # Train
    model, best_acc = train_model(model, train_loader, val_loader, device)

    # Save
    torch.save(model.state_dict(), MODEL_PATH)
    print(f"\n  Model saved to: {MODEL_PATH}")
    print(f"  Labels saved to: {LABELS_PATH}")
    print(f"  Final accuracy: {best_acc:.1%}")

    # Summary
    file_size_mb = os.path.getsize(MODEL_PATH) / (1024 * 1024)
    print(f"  Model file size: {file_size_mb:.1f} MB")
    print("\n  You can now restart test_ui.py -- the upgraded visual_matcher.py")
    print("  will automatically load this model.\n")


if __name__ == "__main__":
    main()
