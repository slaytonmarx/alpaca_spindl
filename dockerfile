FROM python:3.10.12

RUN pip install --upgrade cython
RUN pip install --upgrade pip

WORKDIR /alpaca_spindl
RUN mkdir ./metadata
COPY ./metadata/requirements.txt ./metadata

RUN pip install --upgrade pip

RUN pip3 install --no-cache-dir  -r ./metadata/requirements.txt

ENV PYTHONPATH="${PYTHONPATH}:/alpaca_spindl"

EXPOSE 777

COPY . .

CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=777", "--no-browser", "--allow-root"]

#CMD ["/bin/sh"]