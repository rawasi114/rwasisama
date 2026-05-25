import { Body, Controller, Get, Post, Req } from '@nestjs/common';
import { ApiBearerAuth, ApiOperation, ApiTags } from '@nestjs/swagger';
import { Request } from 'express';
import { Public } from '../../common/decorators/public.decorator';
import { CurrentUser } from '../../common/decorators/current-user.decorator';
import { AuthenticatedUser } from '../../common/types/authenticated-user';
import { AuthService, RequestContext } from './auth.service';
import { LoginDto } from './dto/login.dto';
import { RefreshDto } from './dto/refresh.dto';

function ctxFrom(req: Request): RequestContext {
  return {
    ip: req.ip ?? req.socket?.remoteAddress ?? null,
    userAgent: req.headers['user-agent'] ?? null,
  };
}

@ApiTags('auth')
@Controller('auth')
export class AuthController {
  constructor(private readonly authService: AuthService) {}

  @Public()
  @Post('login')
  @ApiOperation({ summary: 'تسجيل الدخول بالبريد وكلمة المرور' })
  async login(@Body() dto: LoginDto, @Req() req: Request) {
    const { user, tokens } = await this.authService.login(
      dto.email,
      dto.password,
      ctxFrom(req),
    );
    return { user, ...tokens };
  }

  @Public()
  @Post('refresh')
  @ApiOperation({ summary: 'تحديث رمز الوصول باستخدام رمز التحديث' })
  refresh(@Body() dto: RefreshDto, @Req() req: Request) {
    return this.authService.refresh(dto.refreshToken, ctxFrom(req));
  }

  @Post('logout')
  @ApiBearerAuth()
  @ApiOperation({ summary: 'تسجيل الخروج وإبطال رمز التحديث' })
  async logout(@Body() dto: RefreshDto) {
    await this.authService.logout(dto.refreshToken);
    return { success: true };
  }

  @Get('me')
  @ApiBearerAuth()
  @ApiOperation({ summary: 'بيانات المستخدم الحالي وصلاحياته' })
  me(@CurrentUser() user: AuthenticatedUser) {
    return user;
  }
}
