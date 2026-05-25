import {
  Body,
  Controller,
  Get,
  Param,
  ParseUUIDPipe,
  Post,
  UseGuards,
} from '@nestjs/common';
import { ApiBearerAuth, ApiTags } from '@nestjs/swagger';
import { PoliciesGuard } from '../../common/guards/policies.guard';
import { CheckPolicies } from '../../common/decorators/check-policies.decorator';
import { UsersService } from './users.service';
import { CreateUserDto } from './dto/create-user.dto';

@ApiTags('users')
@ApiBearerAuth()
@UseGuards(PoliciesGuard)
@Controller('users')
export class UsersController {
  constructor(private readonly usersService: UsersService) {}

  @Get()
  @CheckPolicies((a) => a.can('read', 'User'))
  findAll() {
    return this.usersService.findAll();
  }

  @Get(':id')
  @CheckPolicies((a) => a.can('read', 'User'))
  findOne(@Param('id', ParseUUIDPipe) id: string) {
    return this.usersService.findById(id);
  }

  @Post()
  @CheckPolicies((a) => a.can('create', 'User'))
  create(@Body() dto: CreateUserDto) {
    return this.usersService.create(dto);
  }
}
