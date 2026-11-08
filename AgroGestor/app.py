
import csv
import io
import os
import re
from datetime import datetime

from flask import (
    Flask,
    render_template,
    session,
    request,
    redirect,
    url_for,
    flash,
    Response,
    jsonify
)

from flask_wtf.csrf import CSRFProtect

from helpers import (
    init_all_tables,
    register_user,
    verify_password,
    get_user_id,
    register_planting,
    get_plantings,
    update_planting,
    delete_planting,
    register_expense,
    get_expenses,
    delete_expense,
    register_harvest,
    get_harvests,
    delete_harvest,
    get_harvest_summary,
    register_sale,
    get_sales,
    delete_sale,
    get_financial_summary,
    get_expenses_by_category,
    get_revenue_by_planting,
    get_production_sales_by_period,
    get_financial_by_planting,
    get_stock_by_planting,
    validar_numero_positivo
)


app = Flask(__name__)

SECRET_KEY = os.environ.get("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError(
        "A variável de ambiente SECRET_KEY não está configurada."
    )

app.config["SECRET_KEY"] = SECRET_KEY

csrf = CSRFProtect(app)

init_all_tables()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("Faça login para acessar o painel.", "error")
        return redirect(url_for("login"))

    user_id = session["user_id"]

    plantacoes = get_plantings(user_id)
    despesas = get_expenses(user_id)
    colheitas = get_harvests(user_id)
    resumo_colheitas = get_harvest_summary(user_id)
    vendas = get_sales(user_id)
    resumo_financeiro = get_financial_summary(user_id)

    estoque_por_plantacao = get_stock_by_planting(user_id)

    total_producao = sum(
        colheita["quantity"] for colheita in colheitas
    )

    return render_template(
        "dashboard.html",
        plantacoes=plantacoes,
        despesas=despesas,
        colheitas=colheitas,
        resumo_colheitas=resumo_colheitas,
        total_producao=total_producao,
        vendas=vendas,
        resumo_financeiro=resumo_financeiro,
        estoque_por_plantacao=estoque_por_plantacao
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        if not username or not email or not password:
            flash("Todos os campos são obrigatórios.", "error")
            return render_template("register.html")

        if len(username) < 3 or len(username) > 30:
            flash(
                "O nome de usuário deve ter entre 3 e 30 caracteres.",
                "error"
            )
            return render_template("register.html")

        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            flash("Informe um endereço de e-mail válido.", "error")
            return render_template("register.html")

        if len(email) > 254:
            flash("O endereço de e-mail é muito longo.", "error")
            return render_template("register.html")

        if len(password) < 8 or len(password) > 128:
            flash(
                "A senha deve ter entre 8 e 128 caracteres.",
                "error"
            )
            return render_template("register.html")

        cadastro = register_user(username, email, password)

        if cadastro:
            flash("Conta criada com sucesso!", "success")
            return redirect(url_for("index"))

        flash(
            "Nome de usuário ou e-mail já cadastrado.",
            "error"
        )

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        usuario_valido = verify_password(username, password)

        if usuario_valido:
            session.clear()
            session["user_id"] = get_user_id(username)

            flash("Login realizado com sucesso!", "success")
            return redirect(url_for("dashboard"))

        flash("Usuário ou senha incorretos.", "error")

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()

    flash("Você saiu da sua conta.", "success")

    return redirect(url_for("index"))


@app.route("/plantings/register", methods=["GET", "POST"])
def plantings_register():
    if "user_id" not in session:
        flash("Faça login para cadastrar uma plantação.", "error")
        return redirect(url_for("login"))

    if request.method == "POST":
        crop_name = request.form.get("crop_name")
        area = request.form.get("area")
        planting_date = request.form.get("planting_date")
        status = request.form.get("status")

        status_validos = [
            "Planejada",
            "Em andamento",
            "Concluída"
        ]

        try:
            area = float(area)

            if (
                not crop_name
                or not validar_numero_positivo(area)
                or not validar_data(planting_date)
                or status not in status_validos
            ):
                flash(
                    "Preencha todos os campos corretamente e informe uma data válida.",
                    "error"
                )
                return redirect(url_for("plantings_register"))

        except (ValueError, TypeError, OverflowError):
            flash("Informe uma área válida.", "error")
            return redirect(url_for("plantings_register"))

        cadastro = register_planting(
            session["user_id"],
            crop_name,
            area,
            planting_date,
            status
        )

        if cadastro:
            flash("Plantação cadastrada com sucesso!", "success")
            return redirect(url_for("dashboard"))

        flash("Não foi possível cadastrar a plantação.", "error")

    return render_template("plantings_register.html")


@app.route("/plantings/<int:planting_id>/edit", methods=["GET", "POST"])
def edit_planting(planting_id):
    if "user_id" not in session:
        flash("Faça login para editar uma plantação.", "error")
        return redirect(url_for("login"))

    user_id = session["user_id"]

    plantacoes = get_plantings(user_id)

    plantacao = next(
        (p for p in plantacoes if p["id"] == planting_id),
        None
    )

    if plantacao is None:
        flash("Plantação não encontrada.", "error")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        crop_name = request.form.get("crop_name")
        area = request.form.get("area")
        planting_date = request.form.get("planting_date")
        status = request.form.get("status")

        try:
            area = float(area)

            if (
                not crop_name
                or not validar_numero_positivo(area)
                or not validar_data(planting_date)
                or status not in ["Planejada", "Em andamento", "Concluída"]
            ):
                flash(
                    "Preencha todos os campos corretamente e informe uma data válida.",
                    "error"
                )
                return redirect(
                    url_for("edit_planting", planting_id=planting_id)
                )

        except (ValueError, TypeError, OverflowError):
            flash("Informe uma área válida.", "error")
            return redirect(
                url_for("edit_planting", planting_id=planting_id)
            )

        atualizado = update_planting(
            user_id,
            planting_id,
            crop_name,
            area,
            planting_date,
            status
        )

        if atualizado:
            flash("Plantação atualizada com sucesso!", "success")
            return redirect(url_for("dashboard"))

        flash("Não foi possível atualizar a plantação.", "error")

    return render_template(
        "plantings_edit.html",
        plantacao=plantacao
    )


@app.route("/plantings/<int:planting_id>/delete", methods=["POST"])
def delete_planting_route(planting_id):
    if "user_id" not in session:
        flash("Faça login para excluir uma plantação.", "error")
        return redirect(url_for("login"))

    excluida = delete_planting(
        session["user_id"],
        planting_id
    )

    if excluida:
        flash("Plantação excluída com sucesso!", "success")
    else:
        flash("Não foi possível excluir a plantação.", "error")

    return redirect(url_for("dashboard"))


@app.route("/expenses/register", methods=["GET", "POST"])
def expenses_register():
    if "user_id" not in session:
        flash("Faça login para cadastrar uma despesa.", "error")
        return redirect(url_for("login"))

    user_id = session["user_id"]

    if request.method == "POST":
        description = request.form.get("description")
        category = request.form.get("category")
        amount = request.form.get("amount")
        expense_date = request.form.get("expense_date")
        planting_id = request.form.get("planting_id")

        try:
            amount = float(amount)

            if (
                not description
                or not category
                or not validar_numero_positivo(amount)
                or not validar_data(expense_date)
            ):
                flash(
                    "Preencha todos os campos corretamente e informe uma data válida.",
                    "error"
                )
                return redirect(url_for("expenses_register"))

            if planting_id:
                planting_id = int(planting_id)
            else:
                planting_id = None

        except (ValueError, TypeError, OverflowError):
            flash("Informe um valor válido.", "error")
            return redirect(url_for("expenses_register"))

        cadastro = register_expense(
            user_id,
            description,
            category,
            amount,
            expense_date,
            planting_id
        )

        if cadastro:
            flash("Despesa cadastrada com sucesso!", "success")
            return redirect(url_for("dashboard"))

        flash("Não foi possível cadastrar a despesa.", "error")

    plantacoes = get_plantings(user_id)

    return render_template(
        "expenses_register.html",
        plantacoes=plantacoes
    )


@app.route("/expenses/<int:expense_id>/delete", methods=["POST"])
def delete_expense_route(expense_id):
    if "user_id" not in session:
        flash("Faça login para excluir uma despesa.", "error")
        return redirect(url_for("login"))

    excluida = delete_expense(
        session["user_id"],
        expense_id
    )

    if excluida:
        flash("Despesa excluída com sucesso!", "success")
    else:
        flash("Não foi possível excluir a despesa.", "error")

    return redirect(url_for("dashboard"))


@app.route("/harvests/register", methods=["GET", "POST"])
def harvests_register():
    if "user_id" not in session:
        flash("Faça login para cadastrar uma colheita.", "error")
        return redirect(url_for("login"))

    user_id = session["user_id"]
    plantacoes = get_plantings(user_id)

    if not plantacoes:
        flash(
            "Cadastre uma plantação antes de registrar uma colheita.",
            "error"
        )
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        planting_id = request.form.get("planting_id")
        quantity = request.form.get("quantity")
        harvest_date = request.form.get("harvest_date")
        notes = request.form.get("notes")

        try:
            planting_id = int(planting_id)
            quantity = float(quantity)

            if (
                not validar_numero_positivo(quantity)
                or not validar_data(harvest_date)
            ):
                flash(
                    "Preencha os campos obrigatórios e informe uma data válida.",
                    "error"
                )
                return redirect(url_for("harvests_register"))

        except (ValueError, TypeError, OverflowError):
            flash(
                "Informe uma plantação e uma quantidade válida.",
                "error"
            )
            return redirect(url_for("harvests_register"))

        cadastro = register_harvest(
            user_id,
            planting_id,
            quantity,
            harvest_date,
            notes
        )

        if cadastro:
            flash("Colheita cadastrada com sucesso!", "success")
            return redirect(url_for("dashboard"))

        flash(
            "Não foi possível cadastrar a colheita. Verifique a plantação selecionada.",
            "error"
        )

    return render_template(
        "harvests_register.html",
        plantacoes=plantacoes
    )


@app.route("/harvests/<int:harvest_id>/delete", methods=["POST"])
def delete_harvest_route(harvest_id):
    if "user_id" not in session:
        flash("Faça login para excluir uma colheita.", "error")
        return redirect(url_for("login"))

    excluida = delete_harvest(
        session["user_id"],
        harvest_id
    )

    if excluida:
        flash("Colheita excluída com sucesso!", "success")
    else:
        flash(
            "Não foi possível excluir a colheita. Verifique se a produção restante cobre as vendas já registradas.",
            "error"
        )

    return redirect(url_for("dashboard"))


@app.route("/sales/register", methods=["GET", "POST"])
def sales_register():
    if "user_id" not in session:
        flash("Faça login para cadastrar uma venda.", "error")
        return redirect(url_for("login"))

    user_id = session["user_id"]
    plantacoes = get_plantings(user_id)

    if not plantacoes:
        flash(
            "Cadastre uma plantação antes de registrar uma venda.",
            "error"
        )
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        planting_id = request.form.get("planting_id")
        quantity = request.form.get("quantity")
        price_per_unit = request.form.get("price_per_unit")
        sale_date = request.form.get("sale_date")
        notes = request.form.get("notes")

        try:
            planting_id = int(planting_id)
            quantity = float(quantity)
            price_per_unit = float(price_per_unit)

            if (
                not validar_numero_positivo(quantity)
                or not validar_numero_positivo(price_per_unit)
                or not validar_data(sale_date)
            ):
                flash(
                    "Preencha os campos obrigatórios e informe uma data válida.",
                    "error"
                )
                return redirect(url_for("sales_register"))

        except (ValueError, TypeError, OverflowError):
            flash("Informe valores válidos para a venda.", "error")
            return redirect(url_for("sales_register"))

        cadastro = register_sale(
            user_id,
            planting_id,
            quantity,
            price_per_unit,
            sale_date,
            notes
        )

        if cadastro:
            flash("Venda cadastrada com sucesso!", "success")
            return redirect(url_for("dashboard"))

        flash(
            "Não foi possível cadastrar a venda. Verifique se há sacas disponíveis para vender.",
            "error"
        )

    estoque_por_plantacao = get_stock_by_planting(user_id)

    return render_template(
        "sales_register.html",
        plantacoes=plantacoes,
        estoque_por_plantacao=estoque_por_plantacao
    )


@app.route("/sales/stock/<int:planting_id>")
def sales_stock(planting_id):
    if "user_id" not in session:
        return jsonify({"error": "Não autorizado"}), 401

    user_id = session["user_id"]
    estoques = get_stock_by_planting(user_id)

    if planting_id not in estoques:
        return jsonify({"error": "Plantação não encontrada"}), 404

    return jsonify({
        "available_stock": estoques[planting_id]
    })


@app.route("/sales/<int:sale_id>/delete", methods=["POST"])
def delete_sale_route(sale_id):
    if "user_id" not in session:
        flash("Faça login para excluir uma venda.", "error")
        return redirect(url_for("login"))

    excluida = delete_sale(
        session["user_id"],
        sale_id
    )

    if excluida:
        flash("Venda excluída com sucesso!", "success")
    else:
        flash("Não foi possível excluir a venda.", "error")

    return redirect(url_for("dashboard"))


# ==================================================
# VALIDACAO DE DATAS
# ==================================================

def validar_data(data):
    try:
        datetime.strptime(data, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


# ==================================================
# RELATORIOS GERENCIAIS
# ==================================================

def validar_periodo(start_date, end_date):
    try:
        if start_date:
            datetime.strptime(start_date, "%Y-%m-%d")

        if end_date:
            datetime.strptime(end_date, "%Y-%m-%d")

        if start_date and end_date and start_date > end_date:
            return False

    except ValueError:
        return False

    return True


def obter_dados_relatorios(user_id, start_date, end_date):
    return {
        "despesas_por_categoria": get_expenses_by_category(
            user_id, start_date, end_date
        ),
        "receitas_por_plantacao": get_revenue_by_planting(
            user_id, start_date, end_date
        ),
        "producao_e_vendas": get_production_sales_by_period(
            user_id, start_date, end_date
        ),
        "resultado_por_plantacao": get_financial_by_planting(
            user_id, start_date, end_date
        )
    }


@app.route("/reports")
def reports():
    if "user_id" not in session:
        flash("Faça login para acessar os relatórios.", "error")
        return redirect(url_for("login"))

    user_id = session["user_id"]

    start_date = request.args.get("start_date") or None
    end_date = request.args.get("end_date") or None

    if not validar_periodo(start_date, end_date):
        flash("Informe um período válido.", "error")
        return redirect(url_for("reports"))

    dados = obter_dados_relatorios(user_id, start_date, end_date)

    return render_template(
        "reports.html",
        **dados,
        start_date=start_date,
        end_date=end_date
    )


# ==================================================
# EXPORTACAO DOS RELATORIOS EM CSV
# ==================================================

@app.route("/reports/export")
def export_reports():
    if "user_id" not in session:
        flash("Faça login para exportar os relatórios.", "error")
        return redirect(url_for("login"))

    user_id = session["user_id"]

    start_date = request.args.get("start_date") or None
    end_date = request.args.get("end_date") or None

    if not validar_periodo(start_date, end_date):
        flash("Informe um período válido para exportação.", "error")
        return redirect(url_for("reports"))

    dados = obter_dados_relatorios(user_id, start_date, end_date)

    arquivo = io.StringIO()
    escritor = csv.writer(arquivo, delimiter=";")

    escritor.writerow(["AGROGESTOR - RELATORIOS GERENCIAIS"])

    if start_date or end_date:
        escritor.writerow([
            "Periodo",
            start_date or "Sem data inicial",
            end_date or "Sem data final"
        ])

    escritor.writerow([])
    escritor.writerow(["1. DESPESAS POR CATEGORIA"])
    escritor.writerow(["Categoria", "Total gasto (R$)"])

    for despesa in dados["despesas_por_categoria"]:
        escritor.writerow([
            despesa["category"],
            f'{despesa["total"]:.2f}'
        ])

    escritor.writerow([])
    escritor.writerow(["2. RECEITAS POR PLANTACAO"])
    escritor.writerow([
        "Plantacao",
        "Quantidade vendida (sacas)",
        "Receita total (R$)"
    ])

    for receita in dados["receitas_por_plantacao"]:
        escritor.writerow([
            receita["crop_name"],
            f'{receita["quantity_sold"]:.2f}',
            f'{receita["total_revenue"]:.2f}'
        ])

    escritor.writerow([])
    escritor.writerow(["3. PRODUCAO E VENDAS POR PLANTACAO"])
    escritor.writerow([
        "Plantacao",
        "Producao (sacas)",
        "Vendas (sacas)",
        "Diferenca (sacas)"
    ])

    for item in dados["producao_e_vendas"]:
        diferenca = item["total_harvested"] - item["total_sold"]

        escritor.writerow([
            item["crop_name"],
            f'{item["total_harvested"]:.2f}',
            f'{item["total_sold"]:.2f}',
            f'{diferenca:.2f}'
        ])

    escritor.writerow([])
    escritor.writerow(["4. RESULTADO FINANCEIRO POR PLANTACAO"])
    escritor.writerow([
        "Plantacao",
        "Receitas (R$)",
        "Despesas (R$)",
        "Saldo (R$)"
    ])

    for resultado in dados["resultado_por_plantacao"]:
        escritor.writerow([
            resultado["crop_name"],
            f'{resultado["total_revenue"]:.2f}',
            f'{resultado["total_expenses"]:.2f}',
            f'{resultado["balance"]:.2f}'
        ])

    conteudo = "\ufeff" + arquivo.getvalue()
    arquivo.close()

    return Response(
        conteudo,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                "attachment; filename=agrogestor_relatorios.csv"
            )
        }
    )


if __name__ == "__main__":
    app.run(debug=False)
