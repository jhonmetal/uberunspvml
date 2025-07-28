# Use the official AWS Lambda Python base image
FROM public.ecr.aws/lambda/python:3.10

# Copy application files to the working directory inside the container
COPY ./webapp/backend ${LAMBDA_TASK_ROOT}

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt 

# Command to run the Lambda function handler
CMD [ "app.main.handler" ] 