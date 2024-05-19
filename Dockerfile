FROM python:3.7.9

WORKDIR /usr/src/app
COPY requirements.txt ./
RUN apt update; apt install -y libgl1
RUN pip install -r requirements.txt
COPY bytetrack-outputs bytetrack-outputs
COPY bytetrack-seg-outputs bytetrack-seg-outputs
COPY deepsort-outputs deepsort-outputs
COPY sort-outputs sort-outputs
COPY videos videos

COPY . .
EXPOSE 7890
CMD [ "python", "./main.py" ]
