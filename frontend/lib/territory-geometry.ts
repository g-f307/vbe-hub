export type TerritoryGeometry = {
  key: string
  version: 'demo-areas-v1'
  center: [number, number]
  polygon: [number, number][]
}

const GEOMETRIES: TerritoryGeometry[] = [
  {
    key: 'manaus--compensa',
    version: 'demo-areas-v1',
    center: [-3.116, -60.069],
    polygon: [
      [-60.088, -3.104],
      [-60.065, -3.099],
      [-60.052, -3.115],
      [-60.061, -3.135],
      [-60.085, -3.132],
      [-60.088, -3.104],
    ],
  },
  {
    key: 'manaus--jorge-teixeira',
    version: 'demo-areas-v1',
    center: [-3.075, -59.927],
    polygon: [
      [-59.947, -3.057],
      [-59.919, -3.051],
      [-59.904, -3.073],
      [-59.918, -3.096],
      [-59.946, -3.088],
      [-59.947, -3.057],
    ],
  },
  {
    key: 'manaus--cidade-nova',
    version: 'demo-areas-v1',
    center: [-3.025, -59.976],
    polygon: [
      [-60.004, -3.006],
      [-59.974, -2.997],
      [-59.951, -3.015],
      [-59.958, -3.044],
      [-59.992, -3.047],
      [-60.004, -3.006],
    ],
  },
]

const GEOMETRY_BY_KEY = new Map(GEOMETRIES.map((geometry) => [geometry.key, geometry]))

export function geometryForArea(municipality: string, district: string): TerritoryGeometry | null {
  return GEOMETRY_BY_KEY.get(`${keyPart(municipality)}--${keyPart(district)}`) ?? null
}

function keyPart(value: string): string {
  return value
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('pt-BR')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
}
