"""
app_demo.py — ponto de entrada do link de DEMONSTRAÇÃO (2026-08-30).

Por que este arquivo existe: o Streamlit Community Cloud não deixa criar um
segundo app hospedado usando o MESMO "Main file path" (app.py) do mesmo
repositório, mesmo com Secrets diferentes — cada app hospedado precisa de
um arquivo principal próprio. Em vez de duplicar todo o código do app.py
aqui (o que criaria duas cópias pra manter sincronizadas), este arquivo só
executa o app.py de verdade — é exatamente o mesmo app, byte a byte.

Como usar: ao criar o segundo app em share.streamlit.io, em vez de
"app.py", coloque "app_demo.py" como "Main file path" — e nos Secrets
desse segundo app, cole só:

    [modo]
    demo = true

(ver README_HOSPEDAGEM.md, Passo 3, e core/data_store.py::_modo_demo_ativo
pra entender como isso ativa a carteira fictícia em vez dos dados reais).
"""

import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parent / "app.py"), run_name="__main__")
