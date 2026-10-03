output "vpc_id" {
  value = aws_vpc.main.id
}

output "subnet_id" {
  value = aws_subnet.public.id
}

output "instance_id" {
  value = aws_instance.web.id
}

output "security_group_id" {
  value = aws_security_group.web.id
}

output "s3_bucket_name" {
  value = aws_s3_bucket.main.id
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.users.name
}

output "sqs_queue_url" {
  value = aws_sqs_queue.main.url
}

output "sns_topic_arn" {
  value = aws_sns_topic.main.arn
}
