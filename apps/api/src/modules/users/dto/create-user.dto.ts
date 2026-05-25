import { ApiProperty } from '@nestjs/swagger';
import {
  IsEmail,
  IsOptional,
  IsString,
  IsUUID,
  MinLength,
} from 'class-validator';

export class CreateUserDto {
  @ApiProperty()
  @IsEmail({}, { message: 'البريد الإلكتروني غير صالح' })
  email!: string;

  @ApiProperty()
  @IsString()
  @MinLength(8, { message: 'كلمة المرور يجب ألا تقل عن 8 أحرف' })
  password!: string;

  @ApiProperty()
  @IsString()
  fullNameAr!: string;

  @ApiProperty({ required: false })
  @IsOptional()
  @IsString()
  fullNameEn?: string;

  @ApiProperty({ required: false })
  @IsOptional()
  @IsString()
  phone?: string;

  @ApiProperty({ description: 'معرّف الدور (Role ID)' })
  @IsUUID()
  roleId!: string;
}
