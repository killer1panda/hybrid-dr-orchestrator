variable "vpc_id" {}
variable "subnet_id" {}
variable "instance_type" { default = "t3.small" }
variable "backup_bucket" {}
variable "tags" { type = map(string) }
variable "ssh_public_key" {}

data "http" "myip" {
  url = "https://ipv4.icanhazip.com"
}

data "aws_ssm_parameter" "ubuntu2204" {
  name = "/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id"
}

resource "aws_security_group" "dr_sg" {
  name        = "dr-ec2-sg"
  description = "Allow HTTP/HTTPS inbound, SSH from Orchestrator."
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    description = "SSH from Orchestrator"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["${chomp(data.http.myip.response_body)}/32"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = merge(var.tags, { Name = "dr-sg" })
}

resource "aws_iam_role" "dr_role" {
  name = "dr_ec2_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.dr_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_policy" "s3_access" {
  name = "dr_ec2_s3_access"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:ListBucket", "s3:PutObject"]
        Resource = [
          "arn:aws:s3:::${var.backup_bucket}",
          "arn:aws:s3:::${var.backup_bucket}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "s3_attach" {
  role       = aws_iam_role.dr_role.name
  policy_arn = aws_iam_policy.s3_access.arn
}

resource "aws_iam_instance_profile" "dr_profile" {
  name = "dr_ec2_profile"
  role = aws_iam_role.dr_role.name
}

resource "aws_key_pair" "dr_key" {
  key_name   = "dr-ssh-key"
  public_key = var.ssh_public_key
  tags       = var.tags
}

resource "aws_instance" "dr" {
  ami                    = data.aws_ssm_parameter.ubuntu2204.value
  instance_type          = var.instance_type
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [aws_security_group.dr_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.dr_profile.name
  key_name               = aws_key_pair.dr_key.key_name

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
  }

  tags = merge(var.tags, { Name = "dr-instance" })
}

resource "aws_eip" "dr_eip" {
  instance = aws_instance.dr.id
  domain   = "vpc"
  tags     = merge(var.tags, { Name = "dr-eip" })
}

output "instance_id" { value = aws_instance.dr.id }
output "public_ip" { value = aws_eip.dr_eip.public_ip }
