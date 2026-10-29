import os
from decimal import Decimal

from flask import abort, flash, redirect, render_template, url_for

from . import products_bp, storage
from .forms import DeleteForm, ProductForm

PLACEHOLDER = 'images/no-image.svg'


@products_bp.app_context_processor
def inject_product_helpers():
    def product_image_url(product):
        """URL зображення товару або заглушка, якщо зображення немає чи файл зник."""
        path = storage.image_file_path(product.get('image'))
        if path and os.path.isfile(path):
            return url_for('products.static', filename=product['image'])
        return url_for('static', filename=PLACEHOLDER)

    return {'product_image_url': product_image_url}


def _get_or_404(product_id):
    product = storage.get_product(product_id)
    if product is None:
        abort(404, description=f'Товар з id {product_id} не знайдено.')
    return product


def _form_to_data(form):
    return {
        'name': form.name.data.strip(),
        'content': form.content.data.strip(),
        'price': float(form.price.data.quantize(Decimal('0.01'))),
        'category': form.category.data,
        'quantity': form.quantity.data,
    }


@products_bp.route('/')
def product_list():
    return render_template('products/products.html', title='Товари',
                           products=storage.all_products(), delete_form=DeleteForm())


@products_bp.route('/<int:product_id>')
def product_detail(product_id):
    product = _get_or_404(product_id)
    return render_template('products/detail_product.html', title=product['name'],
                           product=product, delete_form=DeleteForm())


@products_bp.route('/add', methods=['GET', 'POST'])
def add_product():
    form = ProductForm()

    if form.validate_on_submit():
        data = _form_to_data(form)
        data['image'] = storage.save_image(form.image.data) if form.image.data else None
        product_id = storage.add_product(data)
        flash(f'Товар «{data["name"]}» успішно додано.', 'success')
        return redirect(url_for('products.product_detail', product_id=product_id))

    if form.is_submitted():
        flash('Товар не збережено: виправте помилки у формі.', 'error')

    return render_template('products/product_form.html', title='Додати товар', form=form, product=None)


@products_bp.route('/<int:product_id>/edit', methods=['GET', 'POST'])
def edit_product(product_id):
    product = _get_or_404(product_id)
    # image не передаємо у форму: інакше старий шлях (рядок) опиниться в form.image.data
    initial = {k: v for k, v in product.items() if k != 'image'}
    form = ProductForm(data={**initial, 'price': Decimal(str(product['price']))})

    if form.validate_on_submit():
        data = _form_to_data(form)
        old_image = product.get('image')
        if form.image.data:
            data['image'] = storage.save_image(form.image.data)
        storage.update_product(product_id, data)
        if form.image.data and old_image:
            storage.delete_image(old_image)
        flash(f'Зміни до товару «{data["name"]}» збережено.', 'success')
        return redirect(url_for('products.product_detail', product_id=product_id))

    if form.is_submitted():
        flash('Зміни не збережено: виправте помилки у формі.', 'error')

    return render_template('products/product_form.html', title='Редагувати товар', form=form, product=product)


@products_bp.route('/<int:product_id>/delete', methods=['POST'])
def delete_product(product_id):
    form = DeleteForm()
    if not form.validate_on_submit():
        flash('Не вдалося видалити товар: форма недійсна. Спробуйте ще раз.', 'error')
        return redirect(url_for('products.product_list'))

    product = storage.delete_product(product_id)
    if product is None:
        abort(404, description=f'Товар з id {product_id} не знайдено.')
    storage.delete_image(product.get('image'))
    flash(f'Товар «{product["name"]}» видалено.', 'success')
    return redirect(url_for('products.product_list'))
