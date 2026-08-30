# Pacote "core": regras de negócio, dados e integração com o Yahoo Finance.
# Nada aqui depende do Streamlit (exceto market_data.py, que usa apenas o
# cache do Streamlit) — isso mantém a lógica de cálculo fácil de testar e
# de reaproveitar caso um dia você queira, por exemplo, rodar isso num
# script separado ou numa API.
