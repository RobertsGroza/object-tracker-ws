FROM python:3.7.9

WORKDIR /usr/src/app
COPY requirements.txt ./
RUN apt update; apt install -y libgl1
RUN pip install -r requirements.txt
COPY outputs outputs
COPY videos videos

COPY . .
EXPOSE 7890
CMD [ "python", "./main.py" ]
