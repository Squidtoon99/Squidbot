FROM gorialis/discord.py
WORKDIR /code

# for locale numbers
RUN apt-get update && \
    apt-get install -y locales && \
    sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales

ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8

COPY requirements.txt requirements.txt
RUN pip install --upgrade -r requirements.txt
COPY . .
CMD ["python3", "main.py"]