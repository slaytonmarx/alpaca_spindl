FROM python:3.10.12

RUN pip install --upgrade cython
RUN pip install --upgrade pip

WORKDIR /spindl
RUN mkdir ./metadata
COPY ./metadata/requirements.txt ./metadata

RUN pip install --upgrade pip

RUN pip3 install -r ./metadata/requirements.txt

ENV PYTHONPATH="${PYTHONPATH}:/spindl"

EXPOSE 15000

COPY . .

CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=150000", "--no-browser", "--allow-root"]