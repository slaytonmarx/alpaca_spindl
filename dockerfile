FROM python:3.12

RUN pip install --upgrade cython
RUN pip install --upgrade pip

WORKDIR /spindl
RUN mkdir ./metadata
COPY ./metadata/requirements.txt ./metadata


RUN pip install --upgrade pip

RUN pip3 install --no-cache-dir -r ./metadata/requirements.txt

COPY . .

CMD ["python", "test.py"]