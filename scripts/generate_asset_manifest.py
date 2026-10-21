#!/usr/bin/env python3
import os
import json
import hashlib
from datetime import datetime, timezone

NOW = datetime.now(timezone.utc).isoformat()

ASSET_METADATA = {
    "office-chair": {
        "localPath": "/assets/models/furniture/office-chair.glb",
        "source": "Quaternius Furniture Pack",
        "sourceUrl": "https://raw.githubusercontent.com/benelog/sim-office/main/quaternius/ultimate-furniture/OfficeChair.glb",
        "license": "CC0",
        "author": "Quaternius",
        "intendedUse": "Individual office workstation chair"
    },
    "office-desk": {
        "localPath": "/assets/models/furniture/office-desk.glb",
        "source": "Quaternius Furniture Pack",
        "sourceUrl": "https://raw.githubusercontent.com/benelog/sim-office/main/quaternius/ultimate-furniture/Desk.glb",
        "license": "CC0",
        "author": "Quaternius",
        "intendedUse": "Primary workstation desks for Stark and Usagi"
    },
    "meeting-chair": {
        "localPath": "/assets/models/furniture/meeting-chair.glb",
        "source": "Quaternius Furniture Pack",
        "sourceUrl": "https://raw.githubusercontent.com/benelog/sim-office/main/quaternius/ultimate-furniture/Chair.glb",
        "license": "CC0",
        "author": "Quaternius",
        "intendedUse": "Comfortable chairs for circular central meeting table"
    },
    "table-01": {
        "localPath": "/assets/models/furniture/table-01.glb",
        "source": "Quaternius Furniture Pack",
        "sourceUrl": "https://raw.githubusercontent.com/benelog/sim-office/main/quaternius/ultimate-furniture/Table.glb",
        "license": "CC0",
        "author": "Quaternius",
        "intendedUse": "Meeting table candidate"
    },
    "table-02": {
        "localPath": "/assets/models/furniture/table-02.glb",
        "source": "Quaternius Furniture Pack",
        "sourceUrl": "https://raw.githubusercontent.com/benelog/sim-office/main/quaternius/ultimate-furniture/Table2.glb",
        "license": "CC0",
        "author": "Quaternius",
        "intendedUse": "Side table / meeting table candidate"
    },
    "sofa-01": {
        "localPath": "/assets/models/furniture/sofa-01.glb",
        "source": "Quaternius Furniture Pack",
        "sourceUrl": "https://raw.githubusercontent.com/benelog/sim-office/main/quaternius/ultimate-furniture/Sofa.glb",
        "license": "CC0",
        "author": "Quaternius",
        "intendedUse": "Sofa lounge area"
    },
    "sofa-02": {
        "localPath": "/assets/models/furniture/sofa-02.glb",
        "source": "Quaternius Furniture Pack",
        "sourceUrl": "https://raw.githubusercontent.com/benelog/sim-office/main/quaternius/ultimate-furniture/Sofa2.glb",
        "license": "CC0",
        "author": "Quaternius",
        "intendedUse": "Plush 2-seater lounge sofa"
    },
    "sofa-03": {
        "localPath": "/assets/models/furniture/sofa-03.glb",
        "source": "Quaternius Furniture Pack",
        "sourceUrl": "https://raw.githubusercontent.com/benelog/sim-office/main/quaternius/ultimate-furniture/Sofa3.glb",
        "license": "CC0",
        "author": "Quaternius",
        "intendedUse": "Plush 3-seater lounge sofa"
    },
    "sofa-individual": {
        "localPath": "/assets/models/furniture/sofa-individual.glb",
        "source": "Quaternius Furniture Pack",
        "sourceUrl": "https://raw.githubusercontent.com/benelog/sim-office/main/quaternius/ultimate-furniture/Sofa_individual.glb",
        "license": "CC0",
        "author": "Quaternius",
        "intendedUse": "Single armchair lounge"
    },
    "bookcase-books": {
        "localPath": "/assets/models/furniture/bookcase-books.glb",
        "source": "Quaternius Furniture Pack",
        "sourceUrl": "https://raw.githubusercontent.com/benelog/sim-office/main/quaternius/ultimate-furniture/Bookcase_Books.glb",
        "license": "CC0",
        "author": "Quaternius",
        "intendedUse": "Bookcase with books for back-left office wall"
    },
    "closet": {
        "localPath": "/assets/models/furniture/closet.glb",
        "source": "Quaternius Furniture Pack",
        "sourceUrl": "https://raw.githubusercontent.com/benelog/sim-office/main/quaternius/ultimate-furniture/Closet.glb",
        "license": "CC0",
        "author": "Quaternius",
        "intendedUse": "Tall storage cabinet"
    },
    "short-closet": {
        "localPath": "/assets/models/furniture/short-closet.glb",
        "source": "Quaternius Furniture Pack",
        "sourceUrl": "https://raw.githubusercontent.com/benelog/sim-office/main/quaternius/ultimate-furniture/ShortCloset.glb",
        "license": "CC0",
        "author": "Quaternius",
        "intendedUse": "Low credenza under window wall"
    },
    "night-stand": {
        "localPath": "/assets/models/furniture/night-stand.glb",
        "source": "Quaternius Furniture Pack",
        "sourceUrl": "https://raw.githubusercontent.com/benelog/sim-office/main/quaternius/ultimate-furniture/NightStand.glb",
        "license": "CC0",
        "author": "Quaternius",
        "intendedUse": "Under-desk drawers / side table"
    },
    "wooden-floor-01-diff": {
        "localPath": "/assets/textures/floor/wooden_floor_01_diff_2k.jpg",
        "source": "Poly Haven",
        "sourceUrl": "https://polyhaven.com/a/wooden_floor_01",
        "license": "CC0",
        "author": "Rob Tuytel",
        "intendedUse": "Light oak natural floor diffuse map"
    },
    "wooden-floor-01-nor": {
        "localPath": "/assets/textures/floor/wooden_floor_01_nor_gl_2k.jpg",
        "source": "Poly Haven",
        "sourceUrl": "https://polyhaven.com/a/wooden_floor_01",
        "license": "CC0",
        "author": "Rob Tuytel",
        "intendedUse": "Floor normal map (OpenGL)"
    },
    "wooden-floor-01-rough": {
        "localPath": "/assets/textures/floor/wooden_floor_01_rough_2k.jpg",
        "source": "Poly Haven",
        "sourceUrl": "https://polyhaven.com/a/wooden_floor_01",
        "license": "CC0",
        "author": "Rob Tuytel",
        "intendedUse": "Floor roughness map"
    },
    "wooden-floor-01-ao": {
        "localPath": "/assets/textures/floor/wooden_floor_01_ao_2k.jpg",
        "source": "Poly Haven",
        "sourceUrl": "https://polyhaven.com/a/wooden_floor_01",
        "license": "CC0",
        "author": "Rob Tuytel",
        "intendedUse": "Floor ambient occlusion map"
    },
    "hdri-small-empty-room-3": {
        "localPath": "/assets/hdri/small-empty-room-3.hdr",
        "source": "Poly Haven",
        "sourceUrl": "https://polyhaven.com/a/small_empty_room_3",
        "license": "CC0",
        "author": "Sergej Majboroda",
        "intendedUse": "Realistic indoor environment reflections and soft lighting"
    },
    "prop-computer-screen": {
        "localPath": "/assets/models/props/computer-screen.glb",
        "source": "Kenney Furniture Kit",
        "sourceUrl": "https://kenney.nl/assets/furniture-kit",
        "license": "CC0",
        "author": "Kenney",
        "intendedUse": "Ergonomic slim desktop monitors"
    },
    "prop-computer-keyboard": {
        "localPath": "/assets/models/props/computer-keyboard.glb",
        "source": "Kenney Furniture Kit",
        "sourceUrl": "https://kenney.nl/assets/furniture-kit",
        "license": "CC0",
        "author": "Kenney",
        "intendedUse": "Workstation mechanical keyboards"
    },
    "prop-computer-mouse": {
        "localPath": "/assets/models/props/computer-mouse.glb",
        "source": "Kenney Furniture Kit",
        "sourceUrl": "https://kenney.nl/assets/furniture-kit",
        "license": "CC0",
        "author": "Kenney",
        "intendedUse": "Workstation optical mice"
    },
    "prop-laptop": {
        "localPath": "/assets/models/props/laptop.glb",
        "source": "Kenney Furniture Kit",
        "sourceUrl": "https://kenney.nl/assets/furniture-kit",
        "license": "CC0",
        "author": "Kenney",
        "intendedUse": "Meeting table & desk laptops"
    },
    "prop-lamp-floor": {
        "localPath": "/assets/models/props/lamp-floor.glb",
        "source": "Kenney Furniture Kit",
        "sourceUrl": "https://kenney.nl/assets/furniture-kit",
        "license": "CC0",
        "author": "Kenney",
        "intendedUse": "Warm Scandinavian floor lamp for lounge"
    },
    "prop-lamp-desk": {
        "localPath": "/assets/models/props/lamp-desk.glb",
        "source": "Kenney Furniture Kit",
        "sourceUrl": "https://kenney.nl/assets/furniture-kit",
        "license": "CC0",
        "author": "Kenney",
        "intendedUse": "Workstation desk task lamp"
    },
    "plant-small-1": {
        "localPath": "/assets/models/plants/plant-small-1.glb",
        "source": "Kenney Furniture Kit",
        "sourceUrl": "https://kenney.nl/assets/furniture-kit",
        "license": "CC0",
        "author": "Kenney",
        "intendedUse": "Small succulent desk plant"
    },
    "plant-potted": {
        "localPath": "/assets/models/plants/potted-plant.glb",
        "source": "Kenney Furniture Kit",
        "sourceUrl": "https://kenney.nl/assets/furniture-kit",
        "license": "CC0",
        "author": "Kenney",
        "intendedUse": "Indoor potted greenery"
    }
}

manifest = {"assets": []}
for asset_id, meta in ASSET_METADATA.items():
    rel_path = meta["localPath"].lstrip("/")
    abs_path = os.path.join("public", rel_path)
    file_size = 0
    checksum = ""
    status = "active"
    if os.path.exists(abs_path):
        file_size = os.path.getsize(abs_path)
        checksum = hashlib.sha256(open(abs_path, "rb").read()).hexdigest()
    else:
        status = "missing"
    
    manifest["assets"].append({
        "id": asset_id,
        "localPath": meta["localPath"],
        "source": meta["source"],
        "sourceUrl": meta["sourceUrl"],
        "license": meta["license"],
        "author": meta["author"],
        "intendedUse": meta["intendedUse"],
        "downloadedAt": NOW,
        "fileSizeBytes": file_size,
        "checksumSHA256": checksum,
        "status": status
    })

os.makedirs("public/assets/manifests", exist_ok=True)
with open("public/assets/manifests/ASSET_MANIFEST.json", "w") as f:
    json.dump(manifest, f, indent=2)

print(f"Generated manifest with {len(manifest['assets'])} assets -> public/assets/manifests/ASSET_MANIFEST.json")

