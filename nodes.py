"""
Qwen Multiangle Lightning Node for ComfyUI
Verified Stable Version: 
- Explicit interval checks for elevation.
- Light Position Priority.
- No Shadows.
"""

import numpy as np
from PIL import Image
import base64
import io
import hashlib
import torch

_cache = {}

class QwenMultiangleLightningNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "light_azimuth": ("INT", {
                    "default": 0, "min": 0, "max": 360, "step": 1, "display": "slider"
                }),
                "light_elevation": ("INT", {
                    "default": 30, "min": -90, "max": 90, "step": 1, "display": "slider"
                }),
                "light_intensity": ("FLOAT", {
                    "default": 5.0, "min": 0.0, "max": 10.0, "step": 0.1, "display": "slider"
                }),
                "light_color_hex": ("COLOR", {"default": "#FFFFFF"}),
                "cinematic_mode": ("BOOLEAN", {
                    "default": True, "display": "checkbox"
                }),
            },
            "optional": {
                "image": ("IMAGE",),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("lighting_prompt",)
    FUNCTION = "generate_lighting_prompt"
    CATEGORY = "image/lighting"
    OUTPUT_NODE = True

    def _compute_image_hash(self, image):
        if image is None: return None
        try:
            if hasattr(image, 'cpu'):
                img_np = image[0].cpu().numpy() if len(image.shape) == 4 else image.cpu().numpy()
            else:
                img_np = image.numpy()[0] if hasattr(image, 'numpy') and len(image.shape) == 4 else image
            return hashlib.md5(img_np.tobytes()).hexdigest()
        except Exception:
            return str(hash(str(image)))

    def generate_lighting_prompt(self, light_azimuth, light_elevation, light_intensity, light_color_hex, cinematic_mode=True, image=None, unique_id=None):
        cache_key = str(unique_id) if unique_id else "default"
        image_hash = self._compute_image_hash(image)
        cached = _cache.get(cache_key, {})
        
        if (cached.get('azimuth') == light_azimuth and 
            cached.get('elevation') == light_elevation and 
            cached.get('intensity') == light_intensity and
            cached.get('color') == light_color_hex and
            cached.get('cinematic') == cinematic_mode and
            cached.get('image_hash') == image_hash):
            return cached['result']

        # 1. 方位区间判断
        az = light_azimuth % 360
        if (az >= 337.5) or (az < 22.5): pos_desc = "light source in front"
        elif 22.5 <= az < 67.5: pos_desc = "light source from the front-right"
        elif 67.5 <= az < 112.5: pos_desc = "light source from the right"
        elif 112.5 <= az < 157.5: pos_desc = "light source from the back-right"
        elif 157.5 <= az < 202.5: pos_desc = "light source from behind"
        elif 202.5 <= az < 247.5: pos_desc = "light source from the back-left"
        elif 247.5 <= az < 292.5: pos_desc = "light source from the left"
        else: pos_desc = "light source from the front-left"

        # 2. 高度区间判断 (修正为显式区间，首选底光)
        e = light_elevation
        if -90 <= e < -30:
            elev_desc = "uplighting, light source positioned below the character, light shining upwards"
        elif -30 <= e < -10:
            elev_desc = "low-angle light source from below, upward illumination"
        elif -10 <= e < 20:
            elev_desc = "horizontal level light source"
        elif 20 <= e < 60:
            elev_desc = "high-angle light source"
        else:
            elev_desc = "overhead top-down light source"

        # 3. 强度描述
        if light_intensity < 3.0: int_desc = "soft"
        elif light_intensity < 7.0: int_desc = "bright"
        else: int_desc = "intense"
        
        color_desc = f"colored light ({light_color_hex})"

        # 4. 提示词结构重组 (场景锁定优先 -> 光源位置优先 -> 属性)
        global_constraints = "SCENE LOCK, FIXED VIEWPOINT, maintaining character consistency and pose. RELIGHTING ONLY: "
        light_positioning = f"{pos_desc}, {elev_desc}"
        light_attributes = f"{int_desc} {color_desc}"
        
        if cinematic_mode:
            prompt = f"{global_constraints}{light_positioning}, {light_attributes}, cinematic relighting"
        else:
            prompt = f"{global_constraints}{light_positioning}, {light_attributes}"

        # 预览图处理 (语法闭合检查)
        image_base64 = ""
        if image is not None:
            try:
                i = 255. * image[0].cpu().numpy()
                img_np = np.clip(i, 0, 255).astype(np.uint8)
                pil_image = Image.fromarray(img_np)
                buffer = io.BytesIO()
                pil_image.save(buffer, format="PNG")
                image_base64 = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("utf-8")
            except Exception:
                pass

        result = {"ui": {"image_base64": [image_base64]}, "result": (prompt,)}
        _cache[cache_key] = {
            'azimuth': light_azimuth, 'elevation': light_elevation, 
            'intensity': light_intensity, 'color': light_color_hex,
            'cinematic': cinematic_mode, 'image_hash': image_hash, 
            'result': result
        }
        return result

# 5. 核心节点映射
NODE_CLASS_MAPPINGS = {
    "QwenMultiangleLightningNode": QwenMultiangleLightningNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "QwenMultiangleLightningNode": "Qwen Multiangle Lightning"
}
