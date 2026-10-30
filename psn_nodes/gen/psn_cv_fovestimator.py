"""
PSN_CV_FOVEstimator: Estimates Field of View (FOV) and tilt angle from line segment data.

This node implements the pure-logic geometric estimation part of FOV calculation.
It does not perform image processing (Hough Transform, etc.) but takes pre-extracted
line segments (as a JSON string or list of tuples) and computes:
1. Vanishing points from line intersections.
2. Horizontal and Vertical FOV based on vanishing point geometry and image dimensions.
3. Tilt angle from the horizon line (average angle of horizontal lines).

Inputs:
- lines_json (STRING): JSON array of line segments [[x1, y1, x2, y2], ...]
- image_width (FLOAT): Width of the image in pixels
- image_height (FLOAT): Height of the image in pixels
- reference_width (FLOAT, optional): Known real-world width (not used in pure geometry, kept for interface compatibility)

Outputs:
- fov_horizontal (FLOAT): Estimated horizontal FOV in degrees
- fov_vertical (FLOAT): Estimated vertical FOV in degrees
- tilt_angle (FLOAT): Estimated tilt angle in degrees
"""

import json
import math

CAT = "ParametricStudio/CV"

class PSN_CV_FOVEstimator:
    """Estimates FOV and tilt from line segments using geometric projection."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "lines_json": ("STRING", {"default": "[]", "multiline": True}),
                "image_width": ("FLOAT", {"default": 1024.0, "min": 1.0, "max": 10000.0, "step": 1.0}),
                "image_height": ("FLOAT", {"default": 1024.0, "min": 1.0, "max": 10000.0, "step": 1.0}),
            },
            "optional": {
                "reference_width": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1e6, "step": 0.01}),
            }
        }

    RETURN_TYPES = ("FLOAT", "FLOAT", "FLOAT")
    RETURN_NAMES = ("fov_horizontal", "fov_vertical", "tilt_angle")
    FUNCTION = "run"
    CATEGORY = CAT

    def _parse_lines(self, lines_json):
        """Parse JSON string into list of line segments."""
        try:
            data = json.loads(lines_json)
            if not isinstance(data, list):
                return []
            lines = []
            for item in data:
                if isinstance(item, list) and len(item) == 4:
                    x1, y1, x2, y2 = item
                    if all(isinstance(v, (int, float)) for v in (x1, y1, x2, y2)):
                        lines.append((float(x1), float(y1), float(x2), float(y2)))
            return lines
        except (json.JSONDecodeError, TypeError, ValueError):
            return []

    def _intersect_lines(self, line1, line2):
        """
        Calculate intersection point of two lines.
        Returns (x, y) or None if parallel or coincident.
        """
        x1, y1, x2, y2 = line1
        x3, y3, x4, y4 = line2
        
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 1e-9:
            return None  # Parallel or coincident
            
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        x = x1 + t * (x2 - x1)
        y = y1 + t * (y2 - y1)
        
        return (x, y)

    def _estimate_vanishing_points(self, lines, image_width, image_height):
        """
        Estimate vanishing points by clustering line intersections.
        Returns list of (x, y) vanishing points.
        """
        if len(lines) < 2:
            return []
            
        intersections = []
        for i in range(len(lines)):
            for j in range(i + 1, len(lines)):
                pt = self._intersect_lines(lines[i], lines[j])
                if pt is not None:
                    # Filter out intersections far outside the image (likely noise)
                    # Allow some margin for vanishing points at infinity
                    margin = max(image_width, image_height) * 2
                    if -margin < pt[0] < image_width + margin and -margin < pt[1] < image_height + margin:
                        intersections.append(pt)
        
        if not intersections:
            return []
            
        # Simple clustering: group points within a threshold
        threshold = max(image_width, image_height) * 0.1
        clusters = []
        used = [False] * len(intersections)
        
        for i in range(len(intersections)):
            if used[i]:
                continue
            cluster = [intersections[i]]
            used[i] = True
            for j in range(i + 1, len(intersections)):
                if not used[j]:
                    dx = intersections[i][0] - intersections[j][0]
                    dy = intersections[i][1] - intersections[j][1]
                    if math.sqrt(dx*dx + dy*dy) < threshold:
                        cluster.append(intersections[j])
                        used[j] = True
            if len(cluster) >= 2:  # Require at least 2 lines to form a VP
                cx = sum(p[0] for p in cluster) / len(cluster)
                cy = sum(p[1] for p in cluster) / len(cluster)
                clusters.append((cx, cy))
                
        return clusters

    def _estimate_tilt(self, lines, image_width, image_height):
        """
        Estimate tilt angle from horizontal lines.
        Assumes lines with small angle deviation from horizontal are horizon candidates.
        """
        angles = []
        for x1, y1, x2, y2 in lines:
            dx = x2 - x1
            dy = y2 - y1
            if abs(dx) < 1e-6:
                continue  # Vertical line
            angle = math.atan2(dy, dx) * 180.0 / math.pi
            # Normalize to [-90, 90]
            if angle > 90:
                angle -= 180
            elif angle < -90:
                angle += 180
            # Consider only lines close to horizontal (within 30 degrees)
            if abs(angle) < 30:
                angles.append(angle)
                
        if not angles:
            return 0.0
            
        # Use median to be robust to outliers
        angles.sort()
        median_angle = angles[len(angles) // 2]
        return median_angle

    def _estimate_fov(self, vanishing_points, image_width, image_height):
        """
        Estimate FOV from vanishing points.
        Uses the principal point (center of image) and vanishing points to estimate focal length.
        """
        cx = image_width / 2.0
        cy = image_height / 2.0
        
        if not vanishing_points:
            # Default to a reasonable FOV if no VPs found
            return (60.0, 45.0)
            
        # Use the vanishing point closest to the center for stability
        # Or average multiple VPs if they are close
        vp_x = sum(vp[0] for vp in vanishing_points) / len(vanishing_points)
        vp_y = sum(vp[1] for vp in vanishing_points) / len(vanishing_points)
        
        # Distance from principal point to VP
        dx = vp_x - cx
        dy = vp_y - cy
        
        # If VP is at infinity (very far), FOV is small
        # If VP is close, FOV is large
        # Focal length f = cx / tan(fov_h / 2)
        # For a VP at (vp_x, vp_y), the angle theta = atan2(dy, dx)
        # But we need to relate this to FOV.
        
        # Simplified model: Assume the VP corresponds to the edge of the FOV
        # This is an approximation. A more robust method would use multiple VPs.
        
        # If VP is on the horizontal axis (dy ~ 0), we can estimate horizontal FOV
        if abs(dy) < 1e-6:
            if abs(dx) < 1e-6:
                return (180.0, 180.0)  # VP at center, infinite FOV
            fov_h = 2 * math.atan(cx / abs(dx)) * 180.0 / math.pi
            # Estimate vertical FOV using aspect ratio
            fov_v = 2 * math.atan(cy / abs(dx)) * 180.0 / math.pi
            return (fov_h, fov_v)
        else:
            # VP is not on horizontal axis. Use the distance to estimate focal length
            dist = math.sqrt(dx*dx + dy*dy)
            if dist < 1e-6:
                return (180.0, 180.0)
            
            # Approximate focal length
            f = cx / math.tan(math.atan2(dy, dx)) if abs(dx) > 1e-6 else cy / math.tan(math.atan2(dx, dy))
            if f < 1e-6:
                f = cx  # Default focal length
            
            fov_h = 2 * math.atan(cx / f) * 180.0 / math.pi
            fov_v = 2 * math.atan(cy / f) * 180.0 / math.pi
            return (fov_h, fov_v)

    def run(self, lines_json, image_width, image_height, reference_width=1.0):
        lines = self._parse_lines(lines_json)
        
        if not lines:
            # Return defaults if no lines
            return (60.0, 45.0, 0.0)
            
        vanishing_points = self._estimate_vanishing_points(lines, image_width, image_height)
        tilt = self._estimate_tilt(lines, image_width, image_height)
        fov_h, fov_v = self._estimate_fov(vanishing_points, image_width, image_height)
        
        return (fov_h, fov_v, tilt)

NODE_CLASS_MAPPINGS = {
    "PSN_CV_FOVEstimator": PSN_CV_FOVEstimator
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PSN_CV_FOVEstimator": "CV FOV Estimator"
}
