"""
Qwen Multiangle Lightning Node for ComfyUI
Final Corrected Version: 
1. Scene Lock prioritized in global prompt.
2. Light Position prioritized within lighting description.
3. Pure light source (No shadows).
4. Full UI features and registration.
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

        # 1. 光源方位描述
        az = light_azimuth % 360
        if az < 22.5 or az >= 337.5: pos_desc = "light source in front"
        elif az < 67.5: pos_desc = "light source from the front-right"
        elif az < 112.5: pos_desc = "light source from the right"
        elif az < 157.5: pos_desc = "light source from the back-right"
        elif az < 202.5: pos_desc = "light source from behind"
        elif az < 247.5: pos_desc = "light source from the back-left"
        elif az < 292.5: pos_desc = "light source from the left"
        else: pos_desc = "light source from the front-left"

        # 2. 光源高度描述 (底光逻辑)
        if light_elevation < -30:
            elev_desc = "uplighting, light source positioned below the character, light shining upwards"
        elif light_elevation < -10:
            elev_desc = "low-angle light source from below, upward illumination"
        elif light_elevation < 20:
            elev_desc = "horizontal level light source"
        elif light_elevation < 60:
            elev_desc = "high-angle light source"
        else:
            elev_desc = "overhead top-down light source"

        # 3. 强度与颜色
        if light_intensity < 3.0: int_desc = "soft"
        elif light_intensity < 7.0: int_desc = "bright"
        else: int_desc = "intense"
        
        color_desc = f"colored light ({light_color_hex})"

        # --- 提示词重组 ---
        # 第一层级：场景锁定 (最高优先，保持画面一致)
        global_constraints = "SCENE LOCK, FIXED VIEWPOINT, maintaining character consistency and pose. RELIGHTING ONLY: "
        
        # 第二层级：光源位置 (在重塑任务中首位)
        light_pos_priority = f"{pos_desc}, {elev_desc}"
        
        # 第三层级：光影属性
        light_props = f"{int_desc} {color_desc}"
        
        if cinematic_mode:
            prompt = f"{global_constraints}{light_pos_priority}, {light_props}, cinematic relighting"
        else:
            prompt = f"{global_constraints}{light_pos_priority}, {light_props}"

        # 预览图处理
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

NODE_CLASS_MAPPINGS = {
    "QwenMultiangleLightningNode": QwenMultiangleLightningNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "QwenMultiangleLightningNode": "Qwen Multiangle Lightning"
}
