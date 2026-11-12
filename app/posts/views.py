from datetime import datetime

from flask import flash, redirect, render_template, request, session, url_for

from app import db

from . import post_bp
from .forms import CATEGORY_LABELS, DeletePostForm, PostForm
from .models import Post


@post_bp.app_template_filter('category_label')
def category_label(value):
    """Назва категорії для відображення в шаблонах."""
    return CATEGORY_LABELS.get(value, value or '—')


def get_post_or_404(post_id):
    return db.get_or_404(Post, post_id, description=f'Пост з id {post_id} не знайдено.')


@post_bp.route('', strict_slashes=False)
def all_posts():
    # лише видимі пости, новіші зверху
    stmt = db.select(Post).where(Post.is_active.is_(True)).order_by(Post.posted.desc())
    posts = db.session.scalars(stmt).all()
    return render_template('posts/posts.html', title='Пости', posts=posts)


@post_bp.route('/<int:post_id>')
def detail_post(post_id):
    post = get_post_or_404(post_id)
    return render_template('posts/detail_post.html', title=post.title, post=post)


@post_bp.route('/create', methods=['GET', 'POST'])
def create_post():
    form = PostForm()

    if form.validate_on_submit():
        # автор — користувач із сесії, інакше Anonymous
        post = Post(author=(session.get('user') or 'Anonymous')[:20])
        form.populate_obj(post)  # title, content, is_active, category
        post.posted = form.publish_date.data or datetime.now()
        db.session.add(post)
        db.session.commit()
        flash('Пост успішно додано.', 'success')
        return redirect(url_for('.all_posts'))  # Post/Redirect/Get

    if form.is_submitted():
        flash('Пост не збережено. Перевірте дані у формі!', 'danger')

    return render_template('posts/add_post.html', title='Новий пост', form=form, post=None)


@post_bp.route('/<int:post_id>/update', methods=['GET', 'POST'])
def update_post(post_id):
    post = get_post_or_404(post_id)
    form = PostForm(obj=post)  # заповнення форми даними поста
    form.submit.label.text = 'Зберегти зміни'

    if request.method == 'GET':
        # назви відрізняються (publish_date у формі, posted у моделі), тому заповнюємо вручну
        form.publish_date.data = post.posted

    if form.validate_on_submit():
        form.populate_obj(post)  # оновлення об'єкта post даними з форми
        post.posted = form.publish_date.data or post.posted
        db.session.commit()
        flash('Пост оновлено!', 'success')
        return redirect(url_for('.detail_post', post_id=post.id))

    if form.is_submitted():
        db.session.rollback()
        flash('Зміни не збережено. Перевірте дані у формі!', 'danger')

    return render_template('posts/add_post.html', title='Редагувати пост', form=form, post=post)


@post_bp.route('/<int:post_id>/delete', methods=['GET', 'POST'])
def delete_post(post_id):
    post = get_post_or_404(post_id)
    form = DeletePostForm()

    if form.validate_on_submit():
        db.session.delete(post)
        db.session.commit()
        flash('Пост успішно видалено.', 'success')
        return redirect(url_for('.all_posts'))

    # GET-запит: сторінка підтвердження
    return render_template('posts/delete_confirm.html', title='Видалення поста', post=post, form=form)
