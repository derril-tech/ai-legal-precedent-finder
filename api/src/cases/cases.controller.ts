import {
  Controller,
  Get,
  Post,
  Body,
  Param,
  Query,
  UseGuards,
  Request,
} from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiBearerAuth } from '@nestjs/swagger';
import { CasesService } from './cases.service';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { CreateCaseDto } from './dto/create-case.dto';
import { SearchCasesDto } from './dto/search-cases.dto';
import { Case } from './entities/case.entity';

@ApiTags('cases')
@Controller('cases')
@UseGuards(JwtAuthGuard)
@ApiBearerAuth()
export class CasesController {
  constructor(private readonly casesService: CasesService) {}

  @Post('ingest')
  @ApiOperation({ summary: 'Ingest a new case' })
  @ApiResponse({ status: 201, description: 'Case ingested successfully' })
  async ingestCase(
    @Body() createCaseDto: CreateCaseDto,
    @Request() req: any,
  ) {
    return this.casesService.ingestCase(createCaseDto, req.user.workspaceId);
  }

  @Get()
  @ApiOperation({ summary: 'Search cases' })
  @ApiResponse({ status: 200, description: 'Cases retrieved successfully' })
  async searchCases(
    @Query() searchDto: SearchCasesDto,
    @Request() req: any,
  ) {
    return this.casesService.searchCases(searchDto, req.user.workspaceId);
  }

  @Get(':id')
  @ApiOperation({ summary: 'Get case by ID' })
  @ApiResponse({ status: 200, description: 'Case retrieved successfully' })
  async getCase(@Param('id') id: string, @Request() req: any) {
    return this.casesService.getCase(id, req.user.workspaceId);
  }

  @Get(':id/passages')
  @ApiOperation({ summary: 'Get case passages' })
  @ApiResponse({ status: 200, description: 'Passages retrieved successfully' })
  async getCasePassages(
    @Param('id') id: string,
    @Query('section_type') sectionType?: string,
    @Request() req: any,
  ) {
    return this.casesService.getCasePassages(id, req.user.workspaceId, sectionType);
  }
}
