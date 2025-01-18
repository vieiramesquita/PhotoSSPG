from PIL import Image
import numpy as np
import os
import math
import argparse

# Function to split the photo into gores based on degrees
def split_into_degree_gores(image, output_folder, degree_step=20):
    width, height = image.size
    gore_width = int(width * degree_step / 360)  # Calculate gore width based on degrees

    os.makedirs(output_folder, exist_ok=True)

    gore_files = []
    num_gores = 360 // degree_step
    for i in range(num_gores):
        left = i * gore_width
        right = left + gore_width if i < num_gores - 1 else width

        gore = image.crop((left, 0, right, height))
        gore_file = os.path.join(output_folder, f"gore_{i + 1}.png")
        gore.save(gore_file)
        gore_files.append(gore_file)
        print(f"Gore {i + 1} saved to {gore_file}")

    return gore_files

# Function to apply a spherical sinusoidal transformation to a single gore
def spherical_sinusoidal_projection(image):
    # Initialize result with white background
    width, height = image.size
    pixels = np.array(image)
    result = np.ones_like(pixels) * 255  # White background

    for y in range(height):
        lat = math.pi * (y / height - 0.5)  # Latitude [-π/2, π/2]
        for x in range(width):
            lon = 2 * math.pi * (x / width - 0.5)  # Longitude [-π, π]
            x_sinu = lon * math.cos(lat)
            x_mapped = int((x_sinu + math.pi) / (2 * math.pi) * width)
            y_mapped = y

            if 0 <= x_mapped < width:
                result[y_mapped, x_mapped] = pixels[y, x]
    # Fix gaps in a buffer around the center row
    center_row = height // 2
    buffer = 2  # Number of rows above and below the center row to fix

    for y in range(max(0, center_row - buffer), min(height, center_row + buffer + 1)):
        for x in range(width):  # Include edges for completeness
            if np.all(result[y, x] == 255):  # If pixel is white (empty)
                # Search for valid neighbors in a larger horizontal range
                neighbors = []
                for offset in range(-5, 6):  # Check up to 5 pixels on either side
                    nx = x + offset
                    if 0 <= nx < width and not np.all(result[y, nx] == 255):
                        neighbors.append(result[y, nx])

                # Average neighbors if found
                if neighbors:
                    result[y, x] = np.mean(neighbors, axis=0).astype(result.dtype)
                else:
                    # Propagate the closest valid pixel
                    if x > 0 and not np.all(result[y, x - 1] == 255):
                        result[y, x] = result[y, x - 1]
                    elif x < width - 1 and not np.all(result[y, x + 1] == 255):
                        result[y, x] = result[y, x + 1]

    return Image.fromarray(result)
    
# Function to merge all gores back into a single image
def merge_gores(gore_files, output_file):
    gores = [Image.open(gore_file) for gore_file in gore_files]
    widths, heights = zip(*(gore.size for gore in gores))

    total_width = sum(widths)
    max_height = max(heights)

    merged_image = Image.new("RGB", (total_width, max_height))

    x_offset = 0
    for gore in gores:
        merged_image.paste(gore, (x_offset, 0))
        x_offset += gore.width

    merged_image.save(output_file)
    print(f"Merged image saved to {output_file}")

# Main script with argument parsing
def main():
    parser = argparse.ArgumentParser(description="Process an image into spherical sinusoidal projection with gores.")
    parser.add_argument("--input", required=True, help="Path to the input image file.")
    parser.add_argument("--output_dir", required=True, help="Path to the output directory for gores.")
    parser.add_argument("--output_image", required=True, help="Path to the final merged output image.")
    parser.add_argument("--degree_step", type=int, default=20, help="Degree step for splitting the image into gores (default: 20).")

    args = parser.parse_args()

    # Load the image
    image = Image.open(args.input)

    # Step 1: Split the image into gores based on degrees
    print("Splitting the image into degree-based gores...")
    gore_files = split_into_degree_gores(image, args.output_dir, degree_step=args.degree_step)

    # Step 2: Apply the spherical sinusoidal projection to each gore
    projected_folder = os.path.join(args.output_dir, "projected_gores")
    os.makedirs(projected_folder, exist_ok=True)
    projected_gore_files = []
    for gore_file in gore_files:
        gore_image = Image.open(gore_file)
        print(f"Applying spherical sinusoidal projection to {gore_file}...")
        projected_gore = spherical_sinusoidal_projection(gore_image)
        projected_gore_file = os.path.join(projected_folder, os.path.basename(gore_file))
        projected_gore.save(projected_gore_file)
        projected_gore_files.append(projected_gore_file)
        print(f"Projected gore saved to {projected_gore_file}")

    # Step 3: Merge all projected gores into a single image
    print("Merging all projected gores into a single image...")
    merge_gores(projected_gore_files, args.output_image)

if __name__ == "__main__":
    main()
