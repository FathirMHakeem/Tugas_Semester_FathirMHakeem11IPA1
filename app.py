from flask import Flask, flash, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import os
import secrets
import random

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    cards = db.relationship('Card', backref='subject', lazy=True)

class Card(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(500), nullable=False)
    answer = db.Column(db.String(500), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)

@app.route('/')
def home():
    subjects = Subject.query.all()
    return render_template('home.html', subjects=subjects)

@app.route('/input_subject', methods=['GET', 'POST'])
def input_subject():
    if request.method == 'POST':
        subject_name = request.form['subject'].strip()
        if subject_name:
            existing_subject = Subject.query.filter(
                db.func.lower(Subject.name) == db.func.lower(subject_name)
            ).first()
            
            if existing_subject:
                flash('Subjek sudah ada! Silakan buat flashcard tentang subjek lain.', 'error')
                return redirect(url_for('input_subject'))
            
            new_subject = Subject(name=subject_name)
            db.session.add(new_subject)
            db.session.commit()
            return redirect(url_for('input_cards', subject_id=new_subject.id))
    
    return render_template('input_subject.html')

@app.route('/input_cards/<int:subject_id>', methods=['GET', 'POST'])
def input_cards(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    
    if request.method == 'POST':
        question = request.form['question']
        answer = request.form['answer'].upper()
        
        if question and answer:
            new_card = Card(question=question, answer=answer, subject_id=subject_id)
            db.session.add(new_card)
            db.session.commit()
            
            if 'finish' in request.form:
                return redirect(url_for('home'))
            else:
                return redirect(url_for('input_cards', subject_id=subject_id))
    
    return render_template('input_cards.html', subject=subject)

@app.route('/study/<int:subject_id>', methods=['GET', 'POST'])
def study(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    all_cards = Card.query.filter_by(subject_id=subject_id).all()
    
    if not all_cards:
        return redirect(url_for('home'))
    
    if 'card_order' not in session or session.get('subject_id') != subject_id:
        card_ids = [card.id for card in all_cards]
        random.shuffle(card_ids)
        session['card_order'] = card_ids
        session['current_index'] = 0
        session['subject_id'] = subject_id
        session['results'] = []
    
    current_index = session['current_index']
    
    if current_index >= len(session['card_order']):
        results = session['results']
        session.pop('card_order', None)
        session.pop('current_index', None)
        session.pop('subject_id', None)
        session.pop('results', None)
        return render_template('complete.html', 
                           subject=subject,
                           results=results,
                           correct_count=sum(1 for r in results if r['is_correct']),
                           total_questions=len(results))
    
    current_card_id = session['card_order'][current_index]
    current_card = Card.query.get(current_card_id)
    
    if request.method == 'POST':
        user_answer = request.form['user_answer'].upper()
        card_id = int(request.form['card_id'])
        card = Card.query.get(card_id)
        session['results'].append({
            'question': card.question,
            'correct_answer': card.answer,
            'user_answer': user_answer,
            'is_correct': user_answer == card.answer
        })
        
        session['current_index'] += 1
        
        if session['current_index'] < len(session['card_order']):
            return redirect(url_for('study', subject_id=subject_id))
        else:
            results = session['results']
            session.pop('card_order', None)
            session.pop('current_index', None)
            session.pop('subject_id', None)
            session.pop('results', None)
            return render_template('complete.html', 
                               subject=subject,
                               results=results,
                               correct_count=sum(1 for r in results if r['is_correct']),
                               total_questions=len(results))
    
    return render_template('study.html', 
                         subject=subject, 
                         card=current_card, 
                         current_index=current_index,
                         total_cards=len(all_cards))

@app.route('/delete_subject/<int:subject_id>', methods=['POST'])
def delete_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    Card.query.filter_by(subject_id=subject_id).delete()
    db.session.delete(subject)
    db.session.commit()
    return redirect(url_for('home'))

if __name__ == '__main__':
    with app.app_context():
        if not os.path.exists('instance/data.db'):
            db.create_all()
    app.run(debug=True)