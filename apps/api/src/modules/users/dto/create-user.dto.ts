import { IsEmail, IsOptional, IsString, MinLength } from 'class-validator';

export class CreateUserDto {
  @IsEmail({}, { message: 'بريد إلكتروني غير صالح' })
  email!: string;

  @IsString()
  @MinLength(8, { message: 'كلمة المرور يجب ألا تقل عن ٨ أحرف' })
  password!: string;

  @IsString()
  @MinLength(2)
  fullNameAr!: string;

  @IsOptional()
  @IsString()
  fullNameEn?: string;

  @IsOptional()
  @IsString()
  phone?: string;

  @IsString()
  roleName!: string;
}
