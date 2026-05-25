import { Injectable, UnauthorizedException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { PassportStrategy } from '@nestjs/passport';
import { ExtractJwt, Strategy } from 'passport-jwt';
import { AppConfig } from '../../../config/configuration';
import { AuthenticatedUser } from '../../../common/types/authenticated-user';
import { AuthService } from '../auth.service';

interface JwtPayload {
  sub: string;
}

/** Validates the access JWT and loads the user (with permissions) fresh. */
@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy, 'jwt') {
  constructor(
    config: ConfigService<AppConfig, true>,
    private readonly authService: AuthService,
  ) {
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      ignoreExpiration: false,
      secretOrKey: config.get('jwt', { infer: true }).accessSecret,
    });
  }

  async validate(payload: JwtPayload): Promise<AuthenticatedUser> {
    const user = await this.authService.loadAuthenticatedUser(payload.sub);
    if (!user) {
      throw new UnauthorizedException('المستخدم غير موجود أو غير مفعّل');
    }
    return user;
  }
}
