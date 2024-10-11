FROM python:3.10.12

RUN pip install --upgrade cython
RUN pip install --upgrade pip

WORKDIR /alpaca_spindl
RUN mkdir ./metadata
COPY ./metadata/requirements.txt ./metadata

RUN pip install --upgrade pip

RUN pip3 install -r ./metadata/requirements.txt

ENV PYTHONPATH="${PYTHONPATH}:/alpaca_spindl"

EXPOSE 15000

COPY . .


CMD ["python"]