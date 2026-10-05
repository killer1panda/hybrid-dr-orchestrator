terraform {
  required_version = ">= 1.7.0"
  backend "s3" {
    bucket       = "hybrid-dr-backups-758579869433-ap-southeast-2"
    key          = "state/dr/terraform.tfstate"
    region       = "ap-southeast-2"
    profile      = "dr-sandbox"
    use_lockfile = true
  }
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
    http = {
      source  = "hashicorp/http"
      version = "~> 3.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = "dr-sandbox"

  default_tags {
    tags = {
      Project      = "hybrid-dr"
      Environment  = "dr"
      AutoTeardown = "true"
      ManagedBy    = "terraform"
    }
  }
}

variable "aws_region" { default = "ap-southeast-2" }
variable "backup_bucket" { default = "hybrid-dr-backups-758579869433-ap-southeast-2" }
variable "ssh_public_key" {}

locals {
  tags = {
    Project      = "hybrid-dr"
    Environment  = "dr"
    AutoTeardown = "true"
  }
}

module "vpc" {
  source = "../../modules/vpc"
  az     = "${var.aws_region}a"
  tags   = local.tags
}

module "compute" {
  source         = "../../modules/compute"
  vpc_id         = module.vpc.vpc_id
  subnet_id      = module.vpc.subnet_id
  backup_bucket  = var.backup_bucket
  ssh_public_key = var.ssh_public_key
  tags           = local.tags
}

resource "local_file" "ansible_inventory" {
  content = templatefile("${path.module}/inventory.tmpl", {
    instance_id = module.compute.instance_id
    public_ip   = module.compute.public_ip
  })
  filename = "${path.module}/../../../../ansible/inventory/hosts.ini"
}

output "dr_instance_id" { value = module.compute.instance_id }
output "dr_public_ip" { value = module.compute.public_ip }
