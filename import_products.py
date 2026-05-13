#!/usr/bin/env python

import os
import sys
import csv
import shutil
from pathlib import Path
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TJNaturals.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from django.utils.text import slugify
from django.core.files import File
from shop.models import Product, ProductImage, Category  # Import ProductImage!


def parse_bool(value):
    """Parse boolean from string"""
    if isinstance(value, bool):
        return value
    return str(value).lower() in ('true', '1', 'yes', 'on')


def parse_price(value):
    """Parse price from string"""
    if not value:
        return Decimal('0.00')
    try:
        cleaned = str(value).replace('KSh', '').replace(',', '').replace('$', '').strip()
        return Decimal(cleaned)
    except:
        return Decimal('0.00')


def import_products(csv_file, images_dir):
    """Import products from CSV with images"""
    images_dir = Path(images_dir)
    
    # Use correct media root from settings
    from django.conf import settings
    media_products_dir = Path(settings.MEDIA_ROOT) / 'products'
    media_products_dir.mkdir(parents=True, exist_ok=True)
    
    created = updated = errors = image_success = image_missing = 0
    
    print(f"Importing from: {csv_file}")
    print(f"Images directory: {images_dir}")
    print(f"Media directory: {media_products_dir}")
    print("-" * 50)
    
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for i, row in enumerate(reader, 1):
            try:
                name = row['name'].strip()
                if not name:
                    continue
                
                # Generate SKU if not provided
                sku = row.get('sku', '').strip() or f"TJ-{slugify(name[:3]).upper()}-{i:03d}"
                
                # Get or create category
                category_name = row.get('category', 'General').strip()
                category, _ = Category.objects.get_or_create(
                    name=category_name,
                    defaults={'slug': slugify(category_name)}
                )
                
                # Parse prices
                price = parse_price(row.get('price', 0))
                compare_at_price = parse_price(row.get('compare_at_price', '')) or None
                
                # Parse stock and flags
                stock_quantity = int(row.get('stock_quantity', row.get('stock', 10)))
                weight = Decimal(row.get('weight', 0)) if row.get('weight') else None
                
                is_bestseller = parse_bool(row.get('is_bestseller', False))
                is_special = parse_bool(row.get('is_special', False))
                is_new_arrival = parse_bool(row.get('is_new_arrival', False))
                
                status = row.get('status', 'active').lower()
                if status not in ['active', 'inactive', 'out_of_stock']:
                    status = 'active'
                
                # Check if product exists
                existing = Product.objects.filter(sku=sku).first() or Product.objects.filter(name=name).first()
                
                if existing:
                    # Update existing product
                    existing.name = name
                    existing.description = row.get('description', name)
                    existing.price = price
                    existing.compare_at_price = compare_at_price
                    existing.stock_quantity = stock_quantity
                    existing.category = category
                    existing.status = status
                    existing.weight = weight
                    existing.is_bestseller = is_bestseller
                    existing.is_special = is_special
                    existing.is_new_arrival = is_new_arrival
                    existing.save()
                    product = existing
                    updated += 1
                    action = "Updated"
                else:
                    # Create new product
                    product = Product.objects.create(
                        name=name,
                        description=row.get('description', name),
                        price=price,
                        compare_at_price=compare_at_price,
                        stock_quantity=stock_quantity,
                        category=category,
                        sku=sku,
                        status=status,
                        weight=weight,
                        is_bestseller=is_bestseller,
                        is_special=is_special,
                        is_new_arrival=is_new_arrival
                    )
                    created += 1
                    action = "Created"
                
                print(f"✓ {action}: {name} (SKU: {sku})")
                
                # Handle image - Create ProductImage instance!
                image_name = row.get('image_name', '').strip()
                if image_name:
                    image_path = images_dir / image_name
                    if image_path.exists():
                        try:
                            # Generate unique filename
                            ext = image_path.suffix
                            new_name = f"{product.slug}-{i}{ext}"
                            dest_path = media_products_dir / new_name
                            
                            # Copy file to media directory
                            shutil.copy2(image_path, dest_path)
                            
                            # Create ProductImage instance (NOT product.image!)
                            with open(dest_path, 'rb') as img_file:
                                product_image = ProductImage(
                                    product=product,
                                    alt_text=name,
                                    is_primary=True,
                                    order=0
                                )
                                product_image.image.save(
                                    f"products/{new_name}", 
                                    File(img_file), 
                                    save=True
                                )
                            
                            image_success += 1
                            print(f"  → Image saved: {new_name}")
                        except Exception as img_err:
                            print(f"  ⚠ Image error: {img_err}")
                            import traceback
                            traceback.print_exc()
                    else:
                        image_missing += 1
                        print(f"  ⚠ Image not found: {image_name} (looked in {image_path})")
                        
            except Exception as e:
                errors += 1
                print(f"✗ ERROR with {row.get('name', 'Unknown')}: {e}")
                import traceback
                traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 50)
    print("IMPORT SUMMARY")
    print("=" * 50)
    print(f"Products Created:  {created}")
    print(f"Products Updated:  {updated}")
    print(f"Images Saved:      {image_success}")
    print(f"Images Missing:    {image_missing}")
    print(f"Errors:            {errors}")
    print("=" * 50)


if __name__ == '__main__':
    # UPDATE THESE PATHS
    CSV_FILE = 'products.csv'
    
    # Auto-detect environment (Docker vs local)
    from pathlib import Path
    if Path('/app/images').exists():
        IMAGES_DIR = '/app/images'  # Docker environment
    else:
        IMAGES_DIR = r'C:\Users\USER\Desktop\Tj-Naturals\images'  # Local Windows
    
    import_products(CSV_FILE, IMAGES_DIR)