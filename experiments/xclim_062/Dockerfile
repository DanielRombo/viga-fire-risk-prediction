FROM viga-backend-ml-test:latest
WORKDIR /app
COPY backend/ /app/
COPY experiments/xclim_062/ /prova/
RUN python -m pip freeze > /prova/antes.txt \
    && du -sb /usr/local/lib/python3.11/site-packages > /prova/tamanho_antes.txt \
    && python -m pip install --no-cache-dir -r /app/requirements.txt -c /prova/antes.txt \
    && python -m pip install --no-cache-dir xclim==0.62.0 -c /prova/antes.txt --report /prova/instalacao.json \
    && python -m pip check \
    && python -m pip freeze > /prova/depois.txt \
    && du -sb /usr/local/lib/python3.11/site-packages > /prova/tamanho_depois.txt \
    && python -m services.artefactos_ml
CMD ["python", "/prova/prova.py"]
