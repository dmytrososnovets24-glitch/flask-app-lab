from datetime import datetime

from flask import flash, redirect, render_template, request, url_for
from sqlalchemy.orm import joinedload, selectinload

from app import db

from . import post_bp
from .forms import CATEGORY_LABELS, DeletePostForm, PostForm
from .models import Post, Tag


@post_bp.app_template_filter('category_label')
def category_label(value):
    """Назва категорії для відображення в шаблонах."""
    return CATEGORY_LABELS.get(value, value or '—')


def fill_post(post, form):
    """Переносить дані з форми в об'єкт Post."""
    post.title = form.title.data
    post.content = form.content.data
    post.is_active = form.is_active.data
    post.category = form.category.data
    post.posted = form.publish_date.data or post.posted or datetime.now()
    post.user_id = form.author_id.data
    selected = form.tags.data or []
    post.tags = list(db.session.scalars(
        db.select(Tag).where(Tag.id.in_(selected)).order_by(Tag.name))) if selected else []


def get_post_or_404(post_id):
    return db.get_or_404(Post, post_id, description=f'Пост з id {post_id} не знайдено.')


@post_bp.route('', strict_slashes=False)
def all_posts():
    # лише видимі пости, новіші зверху; автори й теги завантажуються наперед (без N+1)
    stmt = (
        db.select(Post)
        .options(joinedload(Post.user), selectinload(Post.tags))
        .where(Post.is_active.is_(True))
        .order_by(Post.posted.desc())
    )
    tag = request.args.get('tag', '').strip()
    if tag:
        stmt = stmt.where(Post.tags.any(Tag.name == tag))
    posts = db.session.scalars(stmt).all()
    return render_template('posts/posts.html', title='Пости', posts=posts, tag=tag)


@post_bp.route('/<int:post_id>')
def detail_post(post_id):
    post = get_post_or_404(post_id)
    return render_template('posts/detail_post.html', title=post.title, post=post)


@post_bp.route('/create', methods=['GET', 'POST'])
def create_post():
    form = PostForm()

    if form.validate_on_submit():
        post = Post()
        fill_post(post, form)
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
        # назви відрізняються (publish_date / posted, author_id / user_id), тому заповнюємо вручну
        form.publish_date.data = post.posted
        form.author_id.data = post.user_id
        form.tags.data = [tag.id for tag in post.tags]

    if form.validate_on_submit():
        fill_post(post, form)  # оновлення об'єкта post даними з форми
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
