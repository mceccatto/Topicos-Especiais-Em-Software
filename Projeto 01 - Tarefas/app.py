from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SECRET_KEY'] = 'sua_chave_secreta'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Tabela de Associação para Atribuição de Tarefas
tarefa_usuario = db.Table('tarefa_usuario',
    db.Column('tarefa_id', db.Integer, db.ForeignKey('tarefa.id'), primary_key=True),
    db.Column('usuario_id', db.Integer, db.ForeignKey('usuario.id'), primary_key=True)
)

# Modelo de Usuário
class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    tarefas = db.relationship('Tarefa', backref='usuario', lazy=True)
    tarefas_atribuidas = db.relationship('Tarefa', secondary=tarefa_usuario, backref=db.backref('usuarios_atribuidos', lazy='dynamic'))

# Modelo de Tarefa
class Tarefa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(80), nullable=False)
    descricao = db.Column(db.Text)
    status = db.Column(db.String(20), default='pendente')
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# Rotas
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        novo_usuario = Usuario(username=username, password=hashed_password)
        db.session.add(novo_usuario)
        db.session.commit()
        flash('Cadastro realizado com sucesso! Faça login para continuar.', 'success')
        return redirect(url_for('login'))
    return render_template('cadastro.html')

@app.route('/login',
 methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        usuario = Usuario.query.filter_by(username=username).first()
        if usuario and check_password_hash(usuario.password, password):
            login_user(usuario)
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('tarefas'))
        else:
            flash('Credenciais inválidas. Tente novamente.', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('index'))


@app.route('/tarefas')
@login_required
def tarefas():
    status = request.args.get('status')
    if status:
        tarefas_criadas = Tarefa.query.filter_by(usuario_id=current_user.id, status=status).all()
    else:
        tarefas_criadas = Tarefa.query.filter_by(usuario_id=current_user.id).all()
    tarefas_atribuidas = list(current_user.tarefas_atribuidas)
    return render_template('tarefas.html', tarefas_criadas=tarefas_criadas, tarefas_atribuidas=tarefas_atribuidas, status=status)


@app.route('/criar_tarefa', methods=['GET', 'POST'])
@login_required
def criar_tarefa():
    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        nova_tarefa = Tarefa(titulo=titulo, descricao=descricao, usuario_id=current_user.id)
        db.session.add(nova_tarefa)
        db.session.commit()
        flash('Tarefa criada com sucesso!', 'success')
        return redirect(url_for('tarefas'))
    return render_template('criar_tarefa.html')

@app.route('/atribuir_tarefa/<int:id>', methods=['GET', 'POST'])
@login_required
def atribuir_tarefa(id):
    tarefa = Tarefa.query.get_or_404(id)
    if tarefa.usuario_id != current_user.id:
        flash('Você não tem permissão para atribuir esta tarefa.', 'danger')
        return redirect(url_for('tarefas'))

    usuarios = Usuario.query.all()

    if request.method == 'POST':
        try:
            usuario_atribuido_id = request.form['usuario_atribuido']
            usuario_atribuido = Usuario.query.get(usuario_atribuido_id)
            if usuario_atribuido:
                tarefa.usuarios_atribuidos.append(usuario_atribuido)  # Corrigido
                db.session.commit()
                flash('Tarefa atribuída com sucesso!', 'success')
            else:
                flash('Usuário atribuído inválido.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash('Ocorreu um erro ao atribuir a tarefa. Tente novamente.', 'danger')

    return render_template('atribuir_tarefa.html', tarefa=tarefa, usuarios=usuarios)

@app.route('/editar_tarefa/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_tarefa(id):
    tarefa = Tarefa.query.get_or_404(id)
    if tarefa.usuario_id != current_user.id:
        flash('Você não tem permissão para editar esta tarefa.', 'danger')
        return redirect(url_for('tarefas'))

    if request.method == 'POST':
        tarefa.titulo = request.form['titulo']
        tarefa.descricao = request.form['descricao']
        tarefa.status = request.form['status']
        db.session.commit()
        flash('Tarefa editada com sucesso!', 'success')
        return redirect(url_for('tarefas'))
    return render_template('editar_tarefa.html', tarefa=tarefa)

@app.route('/excluir_tarefa/<int:id>')
@login_required
def excluir_tarefa(id):
    tarefa = Tarefa.query.get_or_404(id)
    if tarefa.usuario_id != current_user.id:
        flash('Você não tem permissão para excluir esta tarefa.', 'danger')
        return redirect(url_for('tarefas'))

    db.session.delete(tarefa)
    db.session.commit()
    flash('Tarefa excluída com sucesso!', 'success')
    return redirect(url_for('tarefas'))

if __name__ == '__main__':
    app.run(debug=True)